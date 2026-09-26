from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.audit import journaliser_action_ministerielle
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.email import BrevoEmailClient, EmailDeliveryError, get_email_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_otp_code,
    generate_salt,
    hash_otp_code,
    hash_password,
    verify_password,
)
from app.modules.identite.models import Enseignant, OtpVerification, RoleUtilisateur, Tuteur, Utilisateur
from app.modules.identite.schemas import (
    AdminUtilisateurOut,
    AdminUtilisateurPageOut,
    ChangePasswordRequest,
    EnseignantCreate,
    EnseignantOut,
    LoginRequest,
    MeOut,
    OtpVerifyRequest,
    OtpVerifyResponse,
    ReactiverCompteRequest,
    RefreshRequest,
    SuspendreCompteRequest,
    TokenPair,
    TuteurCreate,
    TuteurOut,
)

router = APIRouter(prefix="/auth/tuteurs", tags=["identite"])

OTP_VALIDITY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def _api_error(status_code: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "message": message, "details": details or {}}},
    )


@router.post("", response_model=TuteurOut, status_code=status.HTTP_201_CREATED)
def creer_compte_tuteur(
    payload: TuteurCreate,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
) -> Utilisateur:
    email_normalise = payload.email.lower()

    if db.query(Utilisateur).filter(Utilisateur.email == email_normalise).first() is not None:
        raise _api_error(
            status.HTTP_409_CONFLICT, "email_deja_utilise", "Un compte existe deja avec cet e-mail."
        )

    utilisateur = Utilisateur(
        nom=payload.nom,
        prenom=payload.prenom,
        login_id=email_normalise,
        email=email_normalise,
        telephone=payload.telephone,
        mot_de_passe_hash=hash_password(payload.mot_de_passe),
        role=RoleUtilisateur.TUTEUR,
        email_verifie=False,
    )
    db.add(utilisateur)
    db.flush()

    db.add(Tuteur(utilisateur_id=utilisateur.id))

    code = generate_otp_code()
    salt = generate_salt()
    db.add(
        OtpVerification(
            utilisateur_id=utilisateur.id,
            code_hash=hash_otp_code(code, salt),
            salt=salt,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_VALIDITY_MINUTES),
        )
    )

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


@router.post("/verify-otp", response_model=OtpVerifyResponse)
def verifier_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> Utilisateur:
    email_normalise = payload.email.lower()
    utilisateur = db.query(Utilisateur).filter(Utilisateur.email == email_normalise).first()
    if utilisateur is None:
        raise _api_error(
            status.HTTP_404_NOT_FOUND, "compte_introuvable", "Aucun compte ne correspond a cet e-mail."
        )

    if utilisateur.email_verifie:
        raise _api_error(status.HTTP_409_CONFLICT, "deja_verifie", "Ce compte est deja verifie.")

    otp = (
        db.query(OtpVerification)
        .filter(OtpVerification.utilisateur_id == utilisateur.id, OtpVerification.utilisee.is_(False))
        .order_by(OtpVerification.created_at.desc())
        .first()
    )
    if otp is None:
        raise _api_error(
            status.HTTP_404_NOT_FOUND, "otp_introuvable", "Aucun code actif, demandez-en un nouveau."
        )

    now = datetime.now(timezone.utc)
    expires_at = otp.expires_at if otp.expires_at.tzinfo else otp.expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        raise _api_error(
            status.HTTP_400_BAD_REQUEST, "otp_expire", "Ce code a expire, demandez-en un nouveau."
        )

    if otp.tentatives >= OTP_MAX_ATTEMPTS:
        raise _api_error(
            status.HTTP_400_BAD_REQUEST,
            "otp_tentatives_epuisees",
            "Trop de tentatives, demandez un nouveau code.",
        )

    if hash_otp_code(payload.code, otp.salt) != otp.code_hash:
        otp.tentatives += 1
        db.commit()
        raise _api_error(status.HTTP_401_UNAUTHORIZED, "otp_invalide", "Code invalide.")

    otp.utilisee = True
    utilisateur.email_verifie = True
    db.commit()
    db.refresh(utilisateur)
    return utilisateur


enseignant_router = APIRouter(prefix="/auth/enseignants", tags=["identite"])


@enseignant_router.post("", response_model=EnseignantOut, status_code=status.HTTP_201_CREATED)
def creer_compte_enseignant(
    payload: EnseignantCreate,
    db: Session = Depends(get_db),
    email_client: BrevoEmailClient = Depends(get_email_client),
) -> Utilisateur:
    """Prealable a UC-04 (candidature) : un enseignant doit avoir un compte verifie avant
    de pouvoir postuler. Meme mecanisme que UC-01 (mot de passe + OTP email)."""
    email_normalise = payload.email.lower()

    if db.query(Utilisateur).filter(Utilisateur.login_id == email_normalise).first() is not None:
        raise _api_error(
            status.HTTP_409_CONFLICT, "email_deja_utilise", "Un compte existe deja avec cet e-mail."
        )

    utilisateur = Utilisateur(
        nom=payload.nom,
        prenom=payload.prenom,
        login_id=email_normalise,
        email=email_normalise,
        telephone=payload.telephone,
        mot_de_passe_hash=hash_password(payload.mot_de_passe),
        role=RoleUtilisateur.ENSEIGNANT,
        email_verifie=False,
    )
    db.add(utilisateur)
    db.flush()

    db.add(Enseignant(utilisateur_id=utilisateur.id))

    code = generate_otp_code()
    salt = generate_salt()
    db.add(
        OtpVerification(
            utilisateur_id=utilisateur.id,
            code_hash=hash_otp_code(code, salt),
            salt=salt,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_VALIDITY_MINUTES),
        )
    )

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


@enseignant_router.post("/verify-otp", response_model=OtpVerifyResponse)
def verifier_otp_enseignant(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> Utilisateur:
    return verifier_otp(payload, db)


auth_router = APIRouter(prefix="/auth", tags=["identite"])
me_router = APIRouter(tags=["identite"])


@auth_router.post("/login", response_model=TokenPair)
def se_connecter(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    utilisateur = db.query(Utilisateur).filter(Utilisateur.login_id == payload.identifiant).first()
    if utilisateur is None or not verify_password(payload.mot_de_passe, utilisateur.mot_de_passe_hash):
        raise _api_error(
            status.HTTP_401_UNAUTHORIZED, "identifiants_invalides", "Identifiant ou mot de passe incorrect."
        )

    if not utilisateur.email_verifie:
        raise _api_error(
            status.HTTP_403_FORBIDDEN, "compte_non_verifie", "Ce compte n'est pas encore verifie."
        )

    return {
        "access_token": create_access_token(utilisateur.id, utilisateur.role.value),
        "refresh_token": create_refresh_token(utilisateur.id),
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

    return {
        "access_token": create_access_token(utilisateur.id, utilisateur.role.value),
        "refresh_token": create_refresh_token(utilisateur.id),
        "doit_changer_mot_de_passe": utilisateur.mot_de_passe_temporaire,
    }


@auth_router.post("/change-password", response_model=MeOut)
def changer_mot_de_passe(
    payload: ChangePasswordRequest,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Utilisateur:
    if not verify_password(payload.ancien_mot_de_passe, utilisateur.mot_de_passe_hash):
        raise _api_error(
            status.HTTP_401_UNAUTHORIZED, "mot_de_passe_incorrect", "Ancien mot de passe incorrect."
        )

    utilisateur.mot_de_passe_hash = hash_password(payload.nouveau_mot_de_passe)
    utilisateur.mot_de_passe_temporaire = False
    db.commit()
    db.refresh(utilisateur)
    return utilisateur


@me_router.get("/me", response_model=MeOut)
def mon_profil(utilisateur: Utilisateur = Depends(get_current_user)) -> Utilisateur:
    return utilisateur


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
