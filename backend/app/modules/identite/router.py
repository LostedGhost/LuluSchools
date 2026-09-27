import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from jose import JWTError
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.audit import journaliser_action_ministerielle
from app.core.database import get_db
from app.core.deps import exiger_compte_actif, get_current_user, require_roles
from app.core.email import BrevoEmailClient, EmailDeliveryError, get_email_client
from app.core.etudiant import est_etudiant as est_etudiant_fn
from app.core.rate_limit import adresse_client, consommer, enregistrer_echec, reinitialiser, verifier_limite
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp_code,
    generate_salt,
    hash_otp_code,
    hash_password,
    otp_correspond,
    refresh_token_revoque,
    verify_password,
    verify_password_factice,
)
from app.modules.identite.models import (
    Enseignant,
    ObjetOtp,
    OtpVerification,
    RoleUtilisateur,
    Tuteur,
    Utilisateur,
)
from app.modules.inscriptions.models import Eleve
from app.modules.identite.schemas import (
    AdminUtilisateurOut,
    AdminUtilisateurPageOut,
    ChangePasswordOut,
    ChangePasswordRequest,
    DemandeEnregistreeOut,
    EnseignantCreate,
    EnseignantOut,
    LoginRequest,
    MeOut,
    MotDePasseOublieRequest,
    OtpVerifyRequest,
    OtpVerifyResponse,
    ReactiverCompteRequest,
    RefreshRequest,
    ReinitialiserMotDePasseRequest,
    RenvoiOtpRequest,
    SuspendreCompteRequest,
    TokenPair,
    TuteurCreate,
    TuteurOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/tuteurs", tags=["identite"])

OTP_VALIDITY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5

_QUART_HEURE = 15 * 60
_HEURE = 60 * 60
_MESSAGE_GENERIQUE_RENVOI = (
    "Si un compte en attente de verification correspond a cette adresse, un nouveau code vient d'etre envoye."
)
_MESSAGE_GENERIQUE_OUBLI = (
    "Si un compte correspond a cet identifiant, un code de reinitialisation vient d'etre envoye "
    "(a l'adresse du tuteur pour un compte eleve)."
)


def _api_error(status_code: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": details or {}}},
    )


def _creer_otp(db: Session, utilisateur: Utilisateur, objet: ObjetOtp) -> str:
    """Invalide les codes encore actifs du meme objet avant d'en emettre un nouveau : un
    seul code valable a la fois par compte et par usage."""
    db.query(OtpVerification).filter(
        OtpVerification.utilisateur_id == utilisateur.id,
        OtpVerification.objet == objet.value,
        OtpVerification.utilisee.is_(False),
    ).update({"utilisee": True}, synchronize_session=False)
    code = generate_otp_code()
    salt = generate_salt()
    db.add(
        OtpVerification(
            utilisateur_id=utilisateur.id,
            objet=objet.value,
            code_hash=hash_otp_code(code, salt),
            salt=salt,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_VALIDITY_MINUTES),
        )
    )
    return code


def _verifier_code(db: Session, utilisateur: Utilisateur, objet: ObjetOtp, code: str, ip: str) -> OtpVerification:
    otp = (
        db.query(OtpVerification)
        .filter(
            OtpVerification.utilisateur_id == utilisateur.id,
            OtpVerification.objet == objet.value,
            OtpVerification.utilisee.is_(False),
        )
        .order_by(OtpVerification.created_at.desc())
        .first()
    )
    if otp is None:
        raise _api_error(status.HTTP_404_NOT_FOUND, "otp_introuvable", "Aucun code actif, demandez-en un nouveau.")

    expires_at = otp.expires_at if otp.expires_at.tzinfo else otp.expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise _api_error(status.HTTP_400_BAD_REQUEST, "otp_expire", "Ce code a expire, demandez-en un nouveau.")

    if otp.tentatives >= OTP_MAX_ATTEMPTS:
        raise _api_error(
            status.HTTP_400_BAD_REQUEST, "otp_tentatives_epuisees", "Trop de tentatives, demandez un nouveau code."
        )

    if not otp_correspond(code, otp.salt, otp.code_hash):
        otp.tentatives += 1
        db.commit()
        enregistrer_echec(db, f"otp:ip:{ip}")
        raise _api_error(status.HTTP_401_UNAUTHORIZED, "otp_invalide", "Code invalide.")
    return otp


def _reponse_inscription_adresse_deja_prise(
    db: Session, existant: Utilisateur, payload: TuteurCreate, email_client: BrevoEmailClient
) -> dict:
    """Anti-enumeration : la reponse est identique a une inscription reussie, que l'adresse
    soit libre ou non - seul le proprietaire de l'adresse est prevenu, par e-mail. Un
    compte existant encore non verifie recoit simplement un nouveau code."""
    try:
        if not existant.email_verifie:
            code = _creer_otp(db, existant, ObjetOtp.VERIFICATION_EMAIL)
            email_client.send_otp_email(to_email=existant.email, to_name=existant.prenom, code=code)
            db.commit()
        else:
            email_client.send_notification_email(
                to_email=existant.email,
                to_name=existant.prenom,
                subject="Tentative d'inscription avec votre adresse",
                message=(
                    "Quelqu'un a tente de creer un compte LuluSchools avec votre adresse e-mail, "
                    "qui possede deja un compte. Si c'etait vous, connectez-vous ou utilisez "
                    "« Mot de passe oublie ». Sinon, vous pouvez ignorer ce message."
                ),
            )
    except EmailDeliveryError:
        db.rollback()
        logger.warning("inscription: echec d'envoi Brevo vers un compte existant (%s)", existant.id)
    return {
        "id": str(uuid.uuid4()),
        "nom": payload.nom.strip(),
        "prenom": payload.prenom.strip(),
        "email": payload.email.lower(),
        "email_verifie": False,
    }


def _creer_compte_avec_otp(
    request: Request,
    payload: TuteurCreate,
    role: RoleUtilisateur,
    db: Session,
    email_client: BrevoEmailClient,
) -> Utilisateur | dict:
    consommer(db, f"inscription:ip:{adresse_client(request)}", 10, _HEURE)
    email_normalise = payload.email.lower()

    existant = (
        db.query(Utilisateur)
        .filter(or_(Utilisateur.email == email_normalise, Utilisateur.login_id == email_normalise))
        .first()
    )
    if existant is not None:
        return _reponse_inscription_adresse_deja_prise(db, existant, payload, email_client)

    utilisateur = Utilisateur(
        nom=payload.nom.strip(),
        prenom=payload.prenom.strip(),
        login_id=email_normalise,
        email=email_normalise,
        telephone=payload.telephone,
        mot_de_passe_hash=hash_password(payload.mot_de_passe),
        role=role,
        email_verifie=False,
    )
    db.add(utilisateur)
    db.flush()
    db.add(Tuteur(utilisateur_id=utilisateur.id) if role == RoleUtilisateur.TUTEUR else Enseignant(utilisateur_id=utilisateur.id))

    code = _creer_otp(db, utilisateur, ObjetOtp.VERIFICATION_EMAIL)
    try:
        email_client.send_otp_email(to_email=utilisateur.email, to_name=utilisateur.prenom, code=code)
    except EmailDeliveryError as exc:
        db.rollback()
        raise _api_error(
            status.HTTP_502_BAD_GATEWAY,
            "envoi_email_echoue",
            "Impossible d'envoyer l'e-mail de verification, veuillez reessayer.",
        ) from exc

    db.commit()
    db.refresh(utilisateur)
    return utilisateur


@router.post("", response_model=TuteurOut, status_code=status.HTTP_201_CREATED)
def creer_compte_tuteur(
    payload: TuteurCreate,
    request: Request,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
) -> Utilisateur | dict:
    return _creer_compte_avec_otp(request, payload, RoleUtilisateur.TUTEUR, db, email_client)


@router.post("/verify-otp", response_model=OtpVerifyResponse)
def verifier_otp(payload: OtpVerifyRequest, request: Request, db: Session = Depends(get_db)) -> Utilisateur:
    ip = adresse_client(request)
    verifier_limite(db, f"otp:ip:{ip}", 30, _QUART_HEURE)
    email_normalise = payload.email.lower()
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == email_normalise).first()
    if utilisateur is None or utilisateur.email_verifie:
        # Meme reponse qu'un code errone : ne revele ni l'existence ni l'etat d'un compte.
        enregistrer_echec(db, f"otp:ip:{ip}")
        raise _api_error(status.HTTP_401_UNAUTHORIZED, "otp_invalide", "Code invalide.")

    otp = _verifier_code(db, utilisateur, ObjetOtp.VERIFICATION_EMAIL, payload.code, ip)
    otp.utilisee = True
    utilisateur.email_verifie = True
    db.commit()
    db.refresh(utilisateur)
    return utilisateur


enseignant_router = APIRouter(prefix="/auth/enseignants", tags=["identite"])


@enseignant_router.post("", response_model=EnseignantOut, status_code=status.HTTP_201_CREATED)
def creer_compte_enseignant(
    payload: EnseignantCreate,
    request: Request,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
) -> Utilisateur | dict:
    """Prealable a UC-04 (candidature) : un enseignant doit avoir un compte verifie avant
    de pouvoir postuler. Meme mecanisme que UC-01 (mot de passe + OTP email)."""
    return _creer_compte_avec_otp(request, payload, RoleUtilisateur.ENSEIGNANT, db, email_client)


@enseignant_router.post("/verify-otp", response_model=OtpVerifyResponse)
def verifier_otp_enseignant(payload: OtpVerifyRequest, request: Request, db: Session = Depends(get_db)) -> Utilisateur:
    return verifier_otp(payload, request, db)


auth_router = APIRouter(prefix="/auth", tags=["identite"])
me_router = APIRouter(tags=["identite"])


@auth_router.post("/otp/renvoyer", response_model=DemandeEnregistreeOut)
def renvoyer_otp(
    payload: RenvoiOtpRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
) -> DemandeEnregistreeOut:
    """Sans lui, un code expire (10 min) ou epuise (5 essais) bloquait le compte a vie :
    la re-inscription renvoie 409 puisque l'e-mail existe deja. Reponse identique que le
    compte existe ou non (pas d'enumeration des adresses)."""
    email_normalise = payload.email.lower()
    consommer(db, f"renvoi_otp:ip:{adresse_client(request)}", 10, _QUART_HEURE)
    consommer(db, f"renvoi_otp:email:{email_normalise}", 3, _QUART_HEURE)

    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == email_normalise).first()
    if utilisateur is not None and not utilisateur.email_verifie:
        code = _creer_otp(db, utilisateur, ObjetOtp.VERIFICATION_EMAIL)
        try:
            email_client.send_otp_email(to_email=utilisateur.email, to_name=utilisateur.prenom, code=code)
            db.commit()
        except EmailDeliveryError:
            db.rollback()
            logger.warning("renvoi_otp: echec d'envoi Brevo pour le compte %s", utilisateur.id)
    return DemandeEnregistreeOut(message=_MESSAGE_GENERIQUE_RENVOI)


def _trouver_par_identifiant(db: Session, identifiant: str) -> Utilisateur | None:
    brut = identifiant.strip()
    utilisateur = db.query(Utilisateur).filter(Utilisateur.login_id == brut).first()
    if utilisateur is None and brut.lower() != brut:
        utilisateur = db.query(Utilisateur).filter(Utilisateur.login_id == brut.lower()).first()
    return utilisateur


def _destinataire_reinitialisation(db: Session, utilisateur: Utilisateur) -> tuple[str, str] | None:
    """Un eleve se connecte par matricule, sans e-mail propre : le code part a son tuteur
    (qui recoit deja ses identifiants provisoires a la validation de l'inscription)."""
    if utilisateur.email:
        return utilisateur.email, utilisateur.prenom
    if utilisateur.role == RoleUtilisateur.ELEVE:
        eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur.id).first()
        tuteur = db.get(Utilisateur, eleve.tuteur_id) if eleve is not None and eleve.tuteur_id else None
        if tuteur is not None and tuteur.email:
            return tuteur.email, tuteur.prenom
    return None


@auth_router.post("/mot-de-passe-oublie", response_model=DemandeEnregistreeOut)
def demander_reinitialisation_mot_de_passe(
    payload: MotDePasseOublieRequest,
    request: Request,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
) -> DemandeEnregistreeOut:
    identifiant = payload.identifiant.strip().lower()
    consommer(db, f"oubli:ip:{adresse_client(request)}", 10, _QUART_HEURE)
    consommer(db, f"oubli:id:{identifiant}", 3, _QUART_HEURE)

    utilisateur = _trouver_par_identifiant(db, payload.identifiant)
    destinataire = _destinataire_reinitialisation(db, utilisateur) if utilisateur is not None else None
    if utilisateur is not None and destinataire is not None:
        code = _creer_otp(db, utilisateur, ObjetOtp.REINITIALISATION_MOT_DE_PASSE)
        try:
            email_client.send_password_reset_email(
                to_email=destinataire[0], to_name=destinataire[1], login_id=utilisateur.login_id, code=code
            )
            db.commit()
        except EmailDeliveryError:
            db.rollback()
            logger.warning("mot_de_passe_oublie: echec d'envoi Brevo pour le compte %s", utilisateur.id)
    return DemandeEnregistreeOut(message=_MESSAGE_GENERIQUE_OUBLI)


@auth_router.post("/mot-de-passe-oublie/confirmer", response_model=DemandeEnregistreeOut)
def reinitialiser_mot_de_passe(
    payload: ReinitialiserMotDePasseRequest, request: Request, db: Session = Depends(get_db)
) -> DemandeEnregistreeOut:
    ip = adresse_client(request)
    verifier_limite(db, f"otp:ip:{ip}", 30, _QUART_HEURE)
    utilisateur = _trouver_par_identifiant(db, payload.identifiant)
    if utilisateur is None:
        enregistrer_echec(db, f"otp:ip:{ip}")
        raise _api_error(status.HTTP_400_BAD_REQUEST, "code_invalide", "Code invalide ou expire.")

    otp = _verifier_code(db, utilisateur, ObjetOtp.REINITIALISATION_MOT_DE_PASSE, payload.code, ip)
    otp.utilisee = True
    utilisateur.mot_de_passe_hash = hash_password(payload.nouveau_mot_de_passe)
    utilisateur.mot_de_passe_temporaire = False
    utilisateur.mot_de_passe_modifie_le = datetime.now(timezone.utc)
    if utilisateur.email:
        utilisateur.email_verifie = True
    db.commit()
    reinitialiser(db, f"login:id:{utilisateur.login_id}")
    return DemandeEnregistreeOut(message="Mot de passe reinitialise. Vous pouvez vous connecter.")


@auth_router.post("/login", response_model=TokenPair)
def se_connecter(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    ip = adresse_client(request)
    identifiant = payload.identifiant.strip()
    cle_identifiant = f"login:id:{identifiant.lower()}"
    verifier_limite(db, cle_identifiant, 10, _QUART_HEURE)
    verifier_limite(db, f"login:ip:{ip}", 50, _QUART_HEURE)

    utilisateur = _trouver_par_identifiant(db, identifiant)
    if utilisateur is None:
        verify_password_factice(payload.mot_de_passe)
    if utilisateur is None or not verify_password(payload.mot_de_passe, utilisateur.mot_de_passe_hash):
        enregistrer_echec(db, cle_identifiant)
        enregistrer_echec(db, f"login:ip:{ip}")
        raise _api_error(
            status.HTTP_401_UNAUTHORIZED, "identifiants_invalides", "Identifiant ou mot de passe incorrect."
        )

    if not utilisateur.email_verifie:
        raise _api_error(
            status.HTTP_403_FORBIDDEN, "compte_non_verifie", "Ce compte n'est pas encore verifie."
        )
    exiger_compte_actif(utilisateur)
    reinitialiser(db, cle_identifiant)

    return {
        "access_token": create_access_token(utilisateur.id, utilisateur.role.value),
        "refresh_token": create_refresh_token(utilisateur.id, utilisateur.mot_de_passe_modifie_le),
        "doit_changer_mot_de_passe": utilisateur.mot_de_passe_temporaire,
    }


@auth_router.post("/refresh", response_model=TokenPair)
def rafraichir_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    try:
        decoded = decode_token(payload.refresh_token)
    except JWTError as exc:
        raise _api_error(
            status.HTTP_401_UNAUTHORIZED, "token_invalide", "Refresh token invalide ou expire."
        ) from exc

    if decoded.get("type") != "refresh":
        raise _api_error(
            status.HTTP_401_UNAUTHORIZED, "token_invalide", "Ce token n'est pas un refresh token."
        )

    utilisateur = db.get(Utilisateur, decoded.get("sub"))
    if utilisateur is None:
        raise _api_error(
            status.HTTP_401_UNAUTHORIZED, "utilisateur_introuvable", "Utilisateur introuvable."
        )
    if refresh_token_revoque(decoded, utilisateur.mot_de_passe_modifie_le):
        raise _api_error(
            status.HTTP_401_UNAUTHORIZED,
            "session_expiree",
            "Le mot de passe a change depuis l'ouverture de cette session : reconnectez-vous.",
        )
    exiger_compte_actif(utilisateur)

    return {
        "access_token": create_access_token(utilisateur.id, utilisateur.role.value),
        "refresh_token": create_refresh_token(utilisateur.id, utilisateur.mot_de_passe_modifie_le),
        "doit_changer_mot_de_passe": utilisateur.mot_de_passe_temporaire,
    }


@auth_router.post("/change-password", response_model=ChangePasswordOut)
def changer_mot_de_passe(
    payload: ChangePasswordRequest,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    cle = f"change_mdp:{utilisateur.id}"
    verifier_limite(db, cle, 10, _QUART_HEURE)
    if not verify_password(payload.ancien_mot_de_passe, utilisateur.mot_de_passe_hash):
        enregistrer_echec(db, cle)
        raise _api_error(
            status.HTTP_401_UNAUTHORIZED, "mot_de_passe_incorrect", "Ancien mot de passe incorrect."
        )
    if payload.ancien_mot_de_passe == payload.nouveau_mot_de_passe:
        raise _api_error(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "mot_de_passe_identique",
            "Le nouveau mot de passe doit etre different de l'ancien.",
        )

    utilisateur.mot_de_passe_hash = hash_password(payload.nouveau_mot_de_passe)
    utilisateur.mot_de_passe_temporaire = False
    utilisateur.mot_de_passe_modifie_le = datetime.now(timezone.utc)
    db.commit()
    db.refresh(utilisateur)
    return {
        **_construire_me_out(db, utilisateur),
        "access_token": create_access_token(utilisateur.id, utilisateur.role.value),
        "refresh_token": create_refresh_token(utilisateur.id, utilisateur.mot_de_passe_modifie_le),
    }


def _construire_me_out(db: Session, utilisateur: Utilisateur) -> dict:
    """UC-57/58 (lot admin etablissement) : `est_etudiant` calcule une seule fois ici et
    reutilise par tout le frontend (ex. gating des micro-jobs cote prestataire) et par les
    deux endpoints qui renvoient un MeOut (`/me`, `/auth/change-password`), plutot que de
    dupliquer la logique - source unique : app.core.etudiant.est_etudiant."""
    eleve = db.query(Eleve).filter(Eleve.utilisateur_id == utilisateur.id).first() if utilisateur.role == RoleUtilisateur.ELEVE else None
    return {
        "id": utilisateur.id,
        "nom": utilisateur.nom,
        "prenom": utilisateur.prenom,
        "login_id": utilisateur.login_id,
        "email": utilisateur.email,
        "role": utilisateur.role,
        "email_verifie": utilisateur.email_verifie,
        "mot_de_passe_temporaire": utilisateur.mot_de_passe_temporaire,
        "est_etudiant": eleve is not None and est_etudiant_fn(db, eleve.id),
    }


@me_router.get("/me", response_model=MeOut)
def mon_profil(db: Session = Depends(get_db), utilisateur: Utilisateur = Depends(get_current_user)) -> dict:
    return _construire_me_out(db, utilisateur)


admin_router = APIRouter(prefix="/admin", tags=["identite"])


@admin_router.get("/utilisateurs", response_model=AdminUtilisateurPageOut)
def lister_utilisateurs_supervision(
    role: RoleUtilisateur | None = None,
    actif: bool | None = None,
    q: str | None = None,
    limit: int = 25,
    offset: int = 0,
    db: Session = Depends(get_db),
    _admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> AdminUtilisateurPageOut:
    """UC-34/49 : liste nationale des utilisateurs - aucun endpoint existant ne permettait
    de retrouver un compte sans deja connaitre son id (le seul filtre transversal existant
    avant ce lot etait la recherche par nom pour l'affectation enseignant<->classe, cf.
    PROJECT_MAP). `q` filtre sur nom/prenom/login_id (email ou matricule). Pagination
    serveur obligatoire (meme regle que l'annuaire etablissements, ADR-009)."""
    limit = max(1, min(limit, 60))
    offset = max(0, offset)

    requete = db.query(Utilisateur)
    if role is not None:
        requete = requete.filter(Utilisateur.role == role)
    if actif is not None:
        requete = requete.filter(Utilisateur.actif == actif)
    if q:
        motif = f"%{q}%"
        requete = requete.filter(
            or_(Utilisateur.nom.ilike(motif), Utilisateur.prenom.ilike(motif), Utilisateur.login_id.ilike(motif))
        )

    total = requete.with_entities(func.count(Utilisateur.id)).scalar() or 0
    items = requete.order_by(Utilisateur.created_at.desc()).offset(offset).limit(limit).all()
    return AdminUtilisateurPageOut(items=items, total=total, limit=limit, offset=offset)


@admin_router.post("/utilisateurs/{utilisateur_id}/suspendre", response_model=AdminUtilisateurOut)
def suspendre_compte(
    utilisateur_id: str,
    payload: SuspendreCompteRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Utilisateur:
    """UC-35/50 : motif obligatoire (voir SuspendreCompteRequest), journalise (UC-36/51).
    Ne peut pas se suspendre soi-meme (evite qu'un A++ se bloque par erreur de manipulation
    sans aucun autre A++ pour le reactiver - decision deleguee, cahier des charges)."""
    cible = db.get(Utilisateur, utilisateur_id)
    if cible is None:
        raise _api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Utilisateur introuvable.")
    if cible.id == admin.id:
        raise _api_error(status.HTTP_409_CONFLICT, "action_impossible", "Vous ne pouvez pas suspendre votre propre compte.")
    if not cible.actif:
        raise _api_error(status.HTTP_409_CONFLICT, "deja_suspendu", "Ce compte est deja suspendu.")

    cible.actif = False
    journaliser_action_ministerielle(db, admin, "utilisateur.suspendre", "utilisateur", cible.id, payload.motif)
    db.commit()
    db.refresh(cible)
    return cible


@admin_router.post("/utilisateurs/{utilisateur_id}/reactiver", response_model=AdminUtilisateurOut)
def reactiver_compte(
    utilisateur_id: str,
    payload: ReactiverCompteRequest,
    db: Session = Depends(get_db),
    admin: Utilisateur = Depends(require_roles(RoleUtilisateur.ADMIN_MINISTERIEL)),
) -> Utilisateur:
    cible = db.get(Utilisateur, utilisateur_id)
    if cible is None:
        raise _api_error(status.HTTP_404_NOT_FOUND, "introuvable", "Utilisateur introuvable.")
    if cible.actif:
        raise _api_error(status.HTTP_409_CONFLICT, "pas_suspendu", "Ce compte n'est pas suspendu.")

    cible.actif = True
    journaliser_action_ministerielle(db, admin, "utilisateur.reactiver", "utilisateur", cible.id, payload.motif)
    db.commit()
    db.refresh(cible)
    return cible
