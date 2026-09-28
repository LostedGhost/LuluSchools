from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles, verifier_portee_etablissement
from app.core.email import BrevoEmailClient, EmailDeliveryError, get_email_client
from app.core.etudiant import est_etudiant as est_etudiant_fn
from app.core.security import generate_temporary_password, hash_password
from app.modules.etablissements.models import (
    AdminEtablissement,
    AffectationEnseignant,
    Classe,
    Etablissement,
    PolitiqueDepassement,
    TypeEtablissement,
)
from app.modules.identite.models import RoleUtilisateur, Tuteur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, Nationalite, StatutInscription
from app.modules.inscriptions.schemas import (
    EleveMeOut,
    InscriptionAvecEleveOut,
    InscriptionCreate,
    InscriptionOut,
    EchecLot,
    LotInscriptionsRequest,
    LotRejetInscriptionsRequest,
    RejetInscriptionRequest,
    ResultatLotInscriptions,
)

router = APIRouter(prefix="/inscriptions", tags=["inscriptions"])
mon_espace_router = APIRouter(tags=["inscriptions"])

AGE_MAJORITE_NUMERIQUE = 16


def _age_a(date_naissance: date) -> int:
    aujourd_hui = date.today()
    age = aujourd_hui.year - date_naissance.year
    if (aujourd_hui.month, aujourd_hui.day) < (date_naissance.month, date_naissance.day):
        age -= 1
    return age


# Format universitaire fourni par l'utilisateur (8 caracteres, verrouille) :
# [1 chiffre nationalite][5 chiffres sequence][2 chiffres annee]
#   - nationalite : 1 = national, 2 = etranger
#   - sequence : incrementee nationalement (tous etablissements du meme cycle confondus),
#     par (cycle, nationalite, annee) - jamais reutilisee, le matricule n'est jamais regenere
#   - annee : 2 derniers chiffres de l'annee de premiere validation
# EP/ES : proposition dans le meme esprit (a confirmer), avec un chiffre de cycle en
# tete pour garantir l'unicite globale sans jamais pouvoir entrer en collision avec le
# format universitaire (8 caracteres, sans chiffre de cycle) : 7=EP, 8=ES -> 9 caracteres.
_PREFIXES_CYCLE_MATRICULE = {
    TypeEtablissement.EP: "7",
    TypeEtablissement.ES: "8",
    TypeEtablissement.UP: "",
    TypeEtablissement.CA: "9",  # jamais utilise (pas d'eleve en centre d'alphabetisation)
}


def _professeur_principal_de(db: Session, classe_id: str) -> tuple[str | None, str | None]:
    """UC-30.3 : le professeur principal d'une classe (voir
    AffectationEnseignant.est_professeur_principal, UC-23) n'etait expose a aucun
    endpoint lisible par ELEVE/TUTEUR - corrige ici pour les deux points d'entree
    "ma classe" (mon_profil_eleve, mes_inscriptions)."""
    affectation = (
        db.query(AffectationEnseignant)
        .filter(AffectationEnseignant.classe_id == classe_id, AffectationEnseignant.est_professeur_principal.is_(True))
        .first()
    )
    if affectation is None:
        return None, None
    enseignant = db.get(Utilisateur, affectation.enseignant_id)
    if enseignant is None:
        return None, None
    return enseignant.nom, enseignant.prenom


def _generer_matricule(db: Session, type_etablissement: TypeEtablissement, nationalite: Nationalite) -> str:
    chiffre_nationalite = "1" if nationalite == Nationalite.NATIONALE else "2"
    annee_suffixe = f"{date.today().year % 100:02d}"
    prefixe_cycle = _PREFIXES_CYCLE_MATRICULE[type_etablissement]

    motif = f"{prefixe_cycle}{chiffre_nationalite}_____{annee_suffixe}"
    deja_attribues = db.query(func.count(Eleve.id)).filter(Eleve.matricule.like(motif)).scalar()
    sequence = f"{deja_attribues + 1:05d}"
    return f"{prefixe_cycle}{chiffre_nationalite}{sequence}{annee_suffixe}"


_STATUTS_INSCRIPTION_ACTIFS = (
    StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL,
    StatutInscription.SOUMISE,
    StatutInscription.VALIDEE,
)


def _enfant_existant(db: Session, tuteur_id: str, payload: InscriptionCreate) -> Eleve | None:
    """Reinscription (rentree suivante, changement de classe) : le tuteur ressaisit
    l'identite de son enfant - on retrouve alors l'Eleve existant plutot que d'en creer
    un doublon qui perdrait matricule, historique et dossier scolaire."""
    for eleve in db.query(Eleve).filter(Eleve.tuteur_id == tuteur_id, Eleve.date_naissance == payload.date_naissance):
        if eleve.nom.strip().lower() == payload.nom.strip().lower() and eleve.prenom.strip().lower() == payload.prenom.strip().lower():
            return eleve
    return None


@router.post("", response_model=InscriptionOut, status_code=status.HTTP_201_CREATED)
def creer_inscription(
    payload: InscriptionCreate,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR, RoleUtilisateur.ELEVE)),
) -> Inscription:
    """UC-02. Seuls le titulaire (l'eleve, pour une reinscription sur son propre compte
    deja existant) et ses tuteurs sont habilites a soumettre une inscription."""
    classe = db.get(Classe, payload.classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "classe_introuvable", "Classe introuvable.")
    etablissement = db.get(Etablissement, classe.etablissement_id)
    if etablissement is not None and etablissement.type == TypeEtablissement.CA:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "centre_alphabetisation",
            "Un centre d'alphabétisation accueille des adultes : inscrivez-vous depuis « Apprendre à lire ».",
        )
    if etablissement is None or not etablissement.actif:
        raise api_error(
            status.HTTP_409_CONFLICT, "etablissement_suspendu", "Cet établissement n'accepte pas d'inscription."
        )

    if utilisateur.role == RoleUtilisateur.ELEVE:
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur.id).first()
        if eleve is None:
            raise api_error(status.HTTP_404_NOT_FOUND, "compte_eleve_introuvable", "Compte élève introuvable.")
    else:
        eleve = _enfant_existant(db, utilisateur.id, payload)
        if eleve is None:
            eleve = Eleve(
                nom=payload.nom.strip(),
                prenom=payload.prenom.strip(),
                date_naissance=payload.date_naissance,
                nationalite=payload.nationalite,
                sexe=payload.sexe,
                tuteur_id=utilisateur.id,
            )
            db.add(eleve)
            db.flush()

    en_cours = (
        db.query(Inscription)
        .filter(
            Inscription.eleve_id == eleve.id,
            Inscription.classe_id == payload.classe_id,
            Inscription.statut.in_(_STATUTS_INSCRIPTION_ACTIFS),
        )
        .first()
    )
    if en_cours is not None:
        raise api_error(
            status.HTTP_409_CONFLICT, "inscription_existante", "Une inscription est déjà en cours ou validée pour cette classe."
        )

    mineur = _age_a(eleve.date_naissance) < AGE_MAJORITE_NUMERIQUE
    # Art. 446 : seul le tuteur peut consentir pour un mineur de moins de 16 ans - la case
    # cochee par l'eleve lui-meme (reinscription depuis son compte) est ignoree.
    if mineur and payload.consentement_parental_donne and utilisateur.role == RoleUtilisateur.TUTEUR:
        statut = StatutInscription.SOUMISE
        horodatage = datetime.now(timezone.utc)
    elif mineur:
        statut = StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL
        horodatage = None
    else:
        statut = StatutInscription.SOUMISE
        horodatage = None

    inscription = Inscription(
        eleve_id=eleve.id,
        classe_id=payload.classe_id,
        statut=statut,
        consentement_parental_horodatage=horodatage,
    )
    db.add(inscription)
    db.commit()
    admettre_automatiquement(db, inscription, email_client)
    db.refresh(inscription)
    return inscription


@router.post("/{inscription_id}/consentement-parental", response_model=InscriptionOut)
def donner_consentement_parental(
    inscription_id: str,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> Inscription:
    inscription = db.get(Inscription, inscription_id)
    if inscription is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Inscription introuvable.")

    eleve = db.get(Eleve, inscription.eleve_id)
    if eleve.tuteur_id != tuteur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet élève n'est pas rattaché à votre compte.")

    if inscription.statut != StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "consentement_non_attendu",
            "Cette inscription n'attend pas de consentement parental.",
        )

    inscription.statut = StatutInscription.SOUMISE
    inscription.consentement_parental_horodatage = datetime.now(timezone.utc)
    db.commit()
    admettre_automatiquement(db, inscription, email_client)
    db.refresh(inscription)
    return inscription


class ValidationImpossible(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code, self.message = code, message


def _places_restantes(db: Session, classe: Classe) -> int:
    prises = (
        db.query(func.count(Inscription.id))
        .filter(Inscription.classe_id == classe.id, Inscription.statut == StatutInscription.VALIDEE)
        .scalar()
    )
    return classe.capacite - prises


def valider_inscription_interne(db: Session, inscription: Inscription, email_client: BrevoEmailClient) -> str | None:
    """Validation d'une inscription SOUMISE (compte eleve, matricule, identifiants envoyes
    au tuteur). Partagee par la validation unitaire, la validation en lot et l'admission
    automatique. Valide et commite, ou leve ValidationImpossible sans rien modifier.
    Renvoie le mot de passe provisoire d'un compte eleve nouvellement cree (None pour une
    reinscription) : pour une inscription au guichet sans compte parent, l'administration
    remet les identifiants imprimes a la famille (saisie_papier)."""
    classe = db.get(Classe, inscription.classe_id)
    if inscription.statut == StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL:
        raise ValidationImpossible("consentement_manquant", "Le consentement parental n'a pas encore été donné.")
    if inscription.statut != StatutInscription.SOUMISE:
        raise ValidationImpossible("statut_invalide", "Cette inscription n'est pas en attente de validation.")
    if _places_restantes(db, classe) <= 0:
        raise ValidationImpossible("classe_complete", "La capacite de cette classe est atteinte.")

    eleve = db.get(Eleve, inscription.eleve_id)
    if eleve.utilisateur_id is not None:
        # Reinscription : le compte et le matricule existent deja et ne sont jamais
        # regeneres (regle du matricule) - aucun nouvel identifiant a envoyer.
        inscription.statut = StatutInscription.VALIDEE
        db.commit()
        return None

    etablissement = db.get(Etablissement, classe.etablissement_id)
    matricule = _generer_matricule(db, etablissement.type, eleve.nationalite)
    mot_de_passe_temporaire = generate_temporary_password()
    utilisateur_eleve = Utilisateur(
        nom=eleve.nom,
        prenom=eleve.prenom,
        login_id=matricule,
        email=None,
        mot_de_passe_hash=hash_password(mot_de_passe_temporaire),
        mot_de_passe_temporaire=True,
        role=RoleUtilisateur.ELEVE,
        email_verifie=True,
    )
    db.add(utilisateur_eleve)
    db.flush()
    eleve.matricule = matricule
    eleve.utilisateur_id = utilisateur_eleve.id

    tuteur = db.get(Tuteur, eleve.tuteur_id)
    tuteur_utilisateur = db.get(Utilisateur, tuteur.utilisateur_id) if tuteur else None
    if tuteur_utilisateur is not None and tuteur_utilisateur.email:
        try:
            email_client.send_temporary_credentials_email(
                to_email=tuteur_utilisateur.email,
                to_name=tuteur_utilisateur.prenom,
                login_id=matricule,
                mot_de_passe=mot_de_passe_temporaire,
            )
        except EmailDeliveryError as exc:
            db.rollback()
            raise ValidationImpossible(
                "envoi_email_echoue", "Impossible d'envoyer les identifiants au tuteur, veuillez réessayer."
            ) from exc

    inscription.statut = StatutInscription.VALIDEE
    db.commit()
    return mot_de_passe_temporaire


def admettre_automatiquement(db: Session, inscription: Inscription, email_client: BrevoEmailClient) -> None:
    """Admission automatique [Delegue] : si l'etablissement l'a activee, une inscription
    SOUMISE est validee sans attendre l'A+, mais seulement pour une classe dont la regle de
    depassement est l'ORDRE D'ARRIVEE (critere objectif fixe par l'etablissement) et tant
    qu'il reste de la place. Decision favorable uniquement : un refus, un concours ou un
    tirage au sort restent des decisions humaines (Art. 401). Au moindre empechement
    (classe complete, e-mail en echec), l'inscription reste simplement SOUMISE."""
    if inscription.statut != StatutInscription.SOUMISE:
        return
    classe = db.get(Classe, inscription.classe_id)
    etablissement = db.get(Etablissement, classe.etablissement_id)
    if not etablissement.admission_automatique or classe.politique_depassement != PolitiqueDepassement.ORDRE_ARRIVEE:
        return
    try:
        valider_inscription_interne(db, inscription, email_client)
    except ValidationImpossible:
        db.refresh(inscription)


@router.post("/{inscription_id}/valider", response_model=InscriptionOut)
def valider_inscription(
    inscription_id: str,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Inscription:
    inscription = db.get(Inscription, inscription_id)
    if inscription is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Inscription introuvable.")
    classe = db.get(Classe, inscription.classe_id)
    verifier_portee_etablissement(db, admin, classe.etablissement_id)
    try:
        valider_inscription_interne(db, inscription, email_client)
    except ValidationImpossible as exc:
        code = status.HTTP_502_BAD_GATEWAY if exc.code == "envoi_email_echoue" else status.HTTP_409_CONFLICT
        raise api_error(code, exc.code, exc.message) from exc
    db.refresh(inscription)
    return inscription


@router.post("/valider-en-lot", response_model=ResultatLotInscriptions)
def valider_inscriptions_en_lot(
    payload: LotInscriptionsRequest,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> ResultatLotInscriptions:
    """Validation groupee, par ordre d'arrivee (les plus anciennes d'abord) : chaque
    inscription est traitee independamment ; celles qui ne peuvent pas l'etre (classe
    complete, consentement manquant...) sont renvoyees avec leur motif."""
    inscriptions = db.query(Inscription).filter(Inscription.id.in_(payload.inscription_ids)).all()
    if len(inscriptions) != len(set(payload.inscription_ids)):
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Une ou plusieurs inscriptions sont introuvables.")
    for inscription in inscriptions:
        verifier_portee_etablissement(db, admin, db.get(Classe, inscription.classe_id).etablissement_id)

    resultat = ResultatLotInscriptions(validees=[], refusees=[])
    for inscription in sorted(inscriptions, key=lambda i: i.created_at):
        try:
            valider_inscription_interne(db, inscription, email_client)
            resultat.validees.append(inscription.id)
        except ValidationImpossible as exc:
            resultat.refusees.append(EchecLot(id=inscription.id, code=exc.code, message=exc.message))
    return resultat


@router.post("/rejeter-en-lot", response_model=ResultatLotInscriptions)
def rejeter_inscriptions_en_lot(
    payload: LotRejetInscriptionsRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> ResultatLotInscriptions:
    """Rejet groupe avec un motif commun (ex. classe complete) - toujours une decision de
    l'A+, jamais automatique."""
    inscriptions = db.query(Inscription).filter(Inscription.id.in_(payload.inscription_ids)).all()
    if len(inscriptions) != len(set(payload.inscription_ids)):
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Une ou plusieurs inscriptions sont introuvables.")
    resultat = ResultatLotInscriptions(validees=[], refusees=[])
    for inscription in inscriptions:
        verifier_portee_etablissement(db, admin, db.get(Classe, inscription.classe_id).etablissement_id)
        if inscription.statut not in (StatutInscription.SOUMISE, StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL):
            resultat.refusees.append(EchecLot(id=inscription.id, code="statut_invalide", message="Inscription déjà traitée."))
            continue
        inscription.statut = StatutInscription.REJETEE
        inscription.motif_rejet = payload.motif
        resultat.validees.append(inscription.id)
    db.commit()
    return resultat


@router.post("/{inscription_id}/rejeter", response_model=InscriptionOut)
def rejeter_inscription(
    inscription_id: str,
    payload: RejetInscriptionRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Inscription:
    inscription = db.get(Inscription, inscription_id)
    if inscription is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Inscription introuvable.")

    classe = db.get(Classe, inscription.classe_id)
    verifier_portee_etablissement(db, admin, classe.etablissement_id)
    if inscription.statut not in (StatutInscription.SOUMISE, StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL):
        raise api_error(
            status.HTTP_409_CONFLICT, "statut_invalide", "Seule une inscription en attente peut être rejetée."
        )

    inscription.statut = StatutInscription.REJETEE
    inscription.motif_rejet = payload.motif
    db.commit()
    db.refresh(inscription)
    return inscription


@router.get("/{inscription_id}", response_model=InscriptionOut)
def obtenir_inscription(
    inscription_id: str,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(
        require_roles(
            RoleUtilisateur.TUTEUR,
            RoleUtilisateur.ELEVE,
            RoleUtilisateur.ADMIN_ETABLISSEMENT,
            RoleUtilisateur.ADMIN_MINISTERIEL,
        )
    ),
) -> Inscription:
    inscription = db.get(Inscription, inscription_id)
    if inscription is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Inscription introuvable.")

    eleve = db.get(Eleve, inscription.eleve_id)
    if utilisateur.role == RoleUtilisateur.TUTEUR:
        if eleve.tuteur_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette inscription ne vous appartient pas.")
    elif utilisateur.role == RoleUtilisateur.ELEVE:
        if eleve.utilisateur_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette inscription ne vous appartient pas.")
    elif utilisateur.role == RoleUtilisateur.ADMIN_ETABLISSEMENT:
        classe = db.get(Classe, inscription.classe_id)
        verifier_portee_etablissement(db, utilisateur, classe.etablissement_id)

    return inscription


def _eleves_par_id(db: Session, inscriptions: list[Inscription]) -> dict[str, Eleve]:
    """Une seule requete pour tous les eleves d'une liste d'inscriptions."""
    ids = {i.eleve_id for i in inscriptions}
    return {e.id: e for e in db.query(Eleve).filter(Eleve.id.in_(ids)).all()} if ids else {}


@mon_espace_router.get(
    "/etablissements/{etablissement_id}/inscriptions-a-valider", response_model=list[InscriptionAvecEleveOut]
)
def inscriptions_a_valider(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT, RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> list[dict]:
    """Ecran A+ : sans cette liste, un admin d'etablissement n'a aucun moyen de savoir
    quelles inscriptions attendent sa validation (UC-02) sans deja connaitre leurs id."""
    verifier_portee_etablissement(db, admin, etablissement_id)

    inscriptions = (
        db.query(Inscription)
        .join(Classe, Classe.id == Inscription.classe_id)
        .filter(Classe.etablissement_id == etablissement_id, Inscription.statut == StatutInscription.SOUMISE)
        .order_by(Inscription.created_at.asc())
        .all()
    )
    eleves = _eleves_par_id(db, inscriptions)
    resultat = []
    for inscription in inscriptions:
        eleve = eleves[inscription.eleve_id]
        resultat.append(
            {
                "id": inscription.id,
                "eleve_id": inscription.eleve_id,
                "classe_id": inscription.classe_id,
                "statut": inscription.statut,
                "consentement_parental_horodatage": inscription.consentement_parental_horodatage,
                "motif_rejet": inscription.motif_rejet,
                "eleve_nom": eleve.nom,
                "eleve_prenom": eleve.prenom,
                "eleve_matricule": eleve.matricule,
                "eleve_utilisateur_id": eleve.utilisateur_id,
            }
        )
    return resultat


@mon_espace_router.get("/tuteurs/me/inscriptions", response_model=list[InscriptionAvecEleveOut])
def mes_inscriptions(
    db: Session = Depends(get_db), tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR))
) -> list[dict]:
    """Permet au tuteur de retrouver ses enfants et l'avancement de leurs demarches sans
    avoir a garder les identifiants d'inscription cote client."""
    inscriptions = (
        db.query(Inscription)
        .join(Eleve, Eleve.id == Inscription.eleve_id)
        .filter(Eleve.tuteur_id == tuteur.id)
        .order_by(Inscription.created_at.desc())
        .all()
    )
    eleves = _eleves_par_id(db, inscriptions)
    resultat = []
    for inscription in inscriptions:
        eleve = eleves[inscription.eleve_id]
        pp_nom, pp_prenom = (
            _professeur_principal_de(db, inscription.classe_id)
            if inscription.statut == StatutInscription.VALIDEE
            else (None, None)
        )
        resultat.append(
            {
                "id": inscription.id,
                "eleve_id": inscription.eleve_id,
                "classe_id": inscription.classe_id,
                "statut": inscription.statut,
                "consentement_parental_horodatage": inscription.consentement_parental_horodatage,
                "motif_rejet": inscription.motif_rejet,
                "eleve_nom": eleve.nom,
                "eleve_prenom": eleve.prenom,
                "eleve_matricule": eleve.matricule,
                "eleve_utilisateur_id": eleve.utilisateur_id,
                "professeur_principal_nom": pp_nom,
                "professeur_principal_prenom": pp_prenom,
            }
        )
    return resultat


@mon_espace_router.get("/eleves/me", response_model=EleveMeOut)
def mon_profil_eleve(
    db: Session = Depends(get_db), eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> dict:
    """Point d'entree du frontend eleve : matricule, nationalite et classe actuelle (via
    la derniere inscription validee), sans quoi il n'y a aucun moyen de savoir dans
    quelle classe naviguer (cours/devoirs/quiz/bulletin)."""
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur.id).first()
    if eleve is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Compte élève introuvable.")

    inscription_validee = (
        db.query(Inscription)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .order_by(Inscription.created_at.desc())
        .first()
    )
    classe = db.get(Classe, inscription_validee.classe_id) if inscription_validee else None
    pp_nom, pp_prenom = _professeur_principal_de(db, classe.id) if classe else (None, None)

    return {
        "id": eleve.utilisateur_id,
        "nom": eleve.nom,
        "prenom": eleve.prenom,
        "matricule": eleve.matricule,
        "nationalite": eleve.nationalite,
        "classe_id": classe.id if classe else None,
        "niveau": classe.niveau if classe else None,
        "etablissement_id": classe.etablissement_id if classe else None,
        "est_etudiant": est_etudiant_fn(db, eleve.id),
        "professeur_principal_nom": pp_nom,
        "professeur_principal_prenom": pp_prenom,
    }
