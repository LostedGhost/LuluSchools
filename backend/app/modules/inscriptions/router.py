from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.core.email import BrevoEmailClient, EmailDeliveryError, get_email_client
from app.core.security import generate_temporary_password, hash_password
from app.modules.etablissements.models import AdminEtablissement, Classe, Etablissement, TypeEtablissement
from app.modules.identite.models import RoleUtilisateur, Tuteur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, Nationalite, StatutInscription
from app.modules.inscriptions.schemas import (
    EleveMeOut,
    InscriptionAvecEleveOut,
    InscriptionCreate,
    InscriptionOut,
    RejetInscriptionRequest,
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
}


def _generer_matricule(db: Session, type_etablissement: TypeEtablissement, nationalite: Nationalite) -> str:
    chiffre_nationalite = "1" if nationalite == Nationalite.NATIONALE else "2"
    annee_suffixe = f"{date.today().year % 100:02d}"
    prefixe_cycle = _PREFIXES_CYCLE_MATRICULE[type_etablissement]

    motif = f"{prefixe_cycle}{chiffre_nationalite}_____{annee_suffixe}"
    deja_attribues = db.query(func.count(Eleve.id)).filter(Eleve.matricule.like(motif)).scalar()
    sequence = f"{deja_attribues + 1:05d}"
    return f"{prefixe_cycle}{chiffre_nationalite}{sequence}{annee_suffixe}"


@router.post("", response_model=InscriptionOut, status_code=status.HTTP_201_CREATED)
def creer_inscription(
    payload: InscriptionCreate,
    db: Session = Depends(get_db),
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR, RoleUtilisateur.ELEVE)),
) -> Inscription:
    """UC-02. Seuls le titulaire (l'eleve, pour une reinscription sur son propre compte
    deja existant) et ses tuteurs sont habilites a soumettre une inscription."""
    classe = db.get(Classe, payload.classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "classe_introuvable", "Classe introuvable.")

    if utilisateur.role == RoleUtilisateur.ELEVE:
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur.id).first()
        if eleve is None:
            raise api_error(status.HTTP_404_NOT_FOUND, "compte_eleve_introuvable", "Compte eleve introuvable.")
    else:
        eleve = Eleve(
            nom=payload.nom,
            prenom=payload.prenom,
            date_naissance=payload.date_naissance,
            nationalite=payload.nationalite,
            tuteur_id=utilisateur.id,
        )
        db.add(eleve)
        db.flush()

    mineur = _age_a(eleve.date_naissance) < AGE_MAJORITE_NUMERIQUE
    if mineur and payload.consentement_parental_donne:
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
    db.refresh(inscription)
    return inscription


@router.post("/{inscription_id}/consentement-parental", response_model=InscriptionOut)
def donner_consentement_parental(
    inscription_id: str,
    db: Session = Depends(get_db),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> Inscription:
    inscription = db.get(Inscription, inscription_id)
    if inscription is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Inscription introuvable.")

    eleve = db.get(Eleve, inscription.eleve_id)
    if eleve.tuteur_id != tuteur.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cet eleve n'est pas rattache a votre compte.")

    if inscription.statut != StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "consentement_non_attendu",
            "Cette inscription n'attend pas de consentement parental.",
        )

    inscription.statut = StatutInscription.SOUMISE
    inscription.consentement_parental_horodatage = datetime.now(timezone.utc)
    db.commit()
    db.refresh(inscription)
    return inscription


@router.post("/{inscription_id}/valider", response_model=InscriptionOut)
def valider_inscription(
    inscription_id: str,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> Inscription:
    inscription = db.get(Inscription, inscription_id)
    if inscription is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Inscription introuvable.")

    classe = db.get(Classe, inscription.classe_id)
    lien_admin = db.get(AdminEtablissement, admin.id)
    if lien_admin is None or lien_admin.etablissement_id != classe.etablissement_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet etablissement.")

    if inscription.statut == StatutInscription.EN_ATTENTE_CONSENTEMENT_PARENTAL:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "consentement_manquant",
            "Le consentement parental n'a pas encore ete donne.",
        )
    if inscription.statut != StatutInscription.SOUMISE:
        raise api_error(
            status.HTTP_409_CONFLICT, "statut_invalide", "Cette inscription n'est pas en attente de validation."
        )

    places_prises = (
        db.query(func.count(Inscription.id))
        .filter(Inscription.classe_id == classe.id, Inscription.statut == StatutInscription.VALIDEE)
        .scalar()
    )
    if places_prises >= classe.capacite:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "classe_complete",
            "La capacite de cette classe est atteinte.",
        )

    eleve = db.get(Eleve, inscription.eleve_id)
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
            raise api_error(
                status.HTTP_502_BAD_GATEWAY,
                "envoi_email_echoue",
                "Impossible d'envoyer les identifiants au tuteur, veuillez reessayer.",
            ) from exc

    inscription.statut = StatutInscription.VALIDEE
    db.commit()
    db.refresh(inscription)
    return inscription


@router.post("/{inscription_id}/rejeter", response_model=InscriptionOut)
def rejeter_inscription(
    inscription_id: str,
    payload: RejetInscriptionRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> Inscription:
    inscription = db.get(Inscription, inscription_id)
    if inscription is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Inscription introuvable.")

    classe = db.get(Classe, inscription.classe_id)
    lien_admin = db.get(AdminEtablissement, admin.id)
    if lien_admin is None or lien_admin.etablissement_id != classe.etablissement_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet etablissement.")

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
        require_roles(RoleUtilisateur.TUTEUR, RoleUtilisateur.ELEVE, RoleUtilisateur.ADMIN_ETABLISSEMENT)
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
    else:
        classe = db.get(Classe, inscription.classe_id)
        lien_admin = db.get(AdminEtablissement, utilisateur.id)
        if lien_admin is None or lien_admin.etablissement_id != classe.etablissement_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet etablissement.")

    return inscription


@mon_espace_router.get(
    "/etablissements/{etablissement_id}/inscriptions-a-valider", response_model=list[InscriptionAvecEleveOut]
)
def inscriptions_a_valider(
    etablissement_id: str,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> list[dict]:
    """Ecran A+ : sans cette liste, un admin d'etablissement n'a aucun moyen de savoir
    quelles inscriptions attendent sa validation (UC-02) sans deja connaitre leurs id."""
    lien = db.get(AdminEtablissement, admin.id)
    if lien is None or lien.etablissement_id != etablissement_id:
        raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet etablissement.")

    inscriptions = (
        db.query(Inscription)
        .join(Classe, Classe.id == Inscription.classe_id)
        .filter(Classe.etablissement_id == etablissement_id, Inscription.statut == StatutInscription.SOUMISE)
        .order_by(Inscription.created_at.asc())
        .all()
    )
    resultat = []
    for inscription in inscriptions:
        eleve = db.get(Eleve, inscription.eleve_id)
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
    resultat = []
    for inscription in inscriptions:
        eleve = db.get(Eleve, inscription.eleve_id)
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


@mon_espace_router.get("/eleves/me", response_model=EleveMeOut)
def mon_profil_eleve(
    db: Session = Depends(get_db), eleve_utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.ELEVE))
) -> dict:
    """Point d'entree du frontend eleve : matricule, nationalite et classe actuelle (via
    la derniere inscription validee), sans quoi il n'y a aucun moyen de savoir dans
    quelle classe naviguer (cours/devoirs/quiz/bulletin)."""
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == eleve_utilisateur.id).first()
    if eleve is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Compte eleve introuvable.")

    inscription_validee = (
        db.query(Inscription)
        .filter(Inscription.eleve_id == eleve.id, Inscription.statut == StatutInscription.VALIDEE)
        .order_by(Inscription.created_at.desc())
        .first()
    )
    classe = db.get(Classe, inscription_validee.classe_id) if inscription_validee else None

    return {
        "id": eleve.utilisateur_id,
        "nom": eleve.nom,
        "prenom": eleve.prenom,
        "matricule": eleve.matricule,
        "nationalite": eleve.nationalite,
        "classe_id": classe.id if classe else None,
        "niveau": classe.niveau if classe else None,
        "etablissement_id": classe.etablissement_id if classe else None,
    }
