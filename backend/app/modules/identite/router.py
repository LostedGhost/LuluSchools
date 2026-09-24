from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.email import BrevoEmailClient, EmailDeliveryError, get_email_client
from app.core.security import generate_otp_code, generate_salt, hash_otp_code, hash_password
from app.modules.identite.models import OtpVerification, RoleUtilisateur, Tuteur, Utilisateur
from app.modules.identite.schemas import (
    OtpVerifyRequest,
    OtpVerifyResponse,
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
