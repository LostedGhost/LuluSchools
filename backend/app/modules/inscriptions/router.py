from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import api_error, require_roles
from app.core.email import BrevoEmailClient, EmailDeliveryError, get_email_client
from app.core.security import generate_temporary_password, hash_password
from app.modules.etablissements.models import AdminEtablissement, Classe, Etablissement
from app.modules.identite.models import RoleUtilisateur, Tuteur, Utilisateur
from app.modules.inscriptions.models import Eleve, Inscription, StatutInscription
from app.modules.inscriptions.schemas import (
    InscriptionCreate,
    InscriptionOut,
    RejetInscriptionRequest,
)

router = APIRouter(prefix="/inscriptions", tags=["inscriptions"])

AGE_MAJORITE_NUMERIQUE = 16


def _age_a(date_naissance: date) -> int:
    aujourd_hui = date.today()
    age = aujourd_hui.year - date_naissance.year
    if (aujourd_hui.month, aujourd_hui.day) < (date_naissance.month, date_naissance.day):
        age -= 1
    return age


def _generer_matricule(db: Session, code_etablissement: str) -> str:
    annee = date.today().year
    sequence = db.query(func.count(Inscription.id)).filter(
        Inscription.statut == StatutInscription.VALIDEE
    ).scalar()
    return f"BJ-{code_etablissement}-{annee}-{sequence + 1:05d}"


@router.post("", response_model=InscriptionOut, status_code=status.HTTP_201_CREATED)
def creer_inscription(
    payload: InscriptionCreate,
    db: Session = Depends(get_db),
    tuteur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR)),
) -> Inscription:
    """UC-02. Seul un tuteur peut soumettre une inscription en Phase 1 : l'auto-inscription
    directe par un eleve de 16 ans ou plus necessiterait un flux de creation de compte
    dedie (symetrique a UC-01) qui n'est pas encore implemente - limitation assumee."""
    classe = db.get(Classe, payload.classe_id)
    if classe is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "classe_introuvable", "Classe introuvable.")

    eleve = Eleve(
        nom=payload.nom,
        prenom=payload.prenom,
        date_naissance=payload.date_naissance,
        tuteur_id=tuteur.id,
    )
    db.add(eleve)
    db.flush()

    mineur = _age_a(payload.date_naissance) < AGE_MAJORITE_NUMERIQUE
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
    matricule = _generer_matricule(db, etablissement.code_etablissement)
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
    utilisateur: Utilisateur = Depends(require_roles(RoleUtilisateur.TUTEUR, RoleUtilisateur.ADMIN_ETABLISSEMENT)),
) -> Inscription:
    inscription = db.get(Inscription, inscription_id)
    if inscription is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Inscription introuvable.")

    if utilisateur.role == RoleUtilisateur.TUTEUR:
        eleve = db.get(Eleve, inscription.eleve_id)
        if eleve.tuteur_id != utilisateur.id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Cette inscription ne vous appartient pas.")
    else:
        classe = db.get(Classe, inscription.classe_id)
        lien_admin = db.get(AdminEtablissement, utilisateur.id)
        if lien_admin is None or lien_admin.etablissement_id != classe.etablissement_id:
            raise api_error(status.HTTP_403_FORBIDDEN, "acces_refuse", "Vous n'administrez pas cet etablissement.")

    return inscription
