import re

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

_PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*\d).{8,}$")


class TuteurCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str
    prenom: str
    email: EmailStr
    telephone: str | None = None
    mot_de_passe: str

    @field_validator("mot_de_passe")
    @classmethod
    def _valider_force_mot_de_passe(cls, value: str) -> str:
        if not _PASSWORD_PATTERN.match(value):
            raise ValueError(
                "Le mot de passe doit contenir au moins 8 caracteres, une majuscule et un chiffre."
            )
        return value


class TuteurOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    nom: str
    prenom: str
    email: EmailStr
    email_verifie: bool


class OtpVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    code: str


class OtpVerifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    email: EmailStr
    email_verifie: bool


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifiant: str  # e-mail (tuteur/enseignant/admin) ou matricule (eleve)
    mot_de_passe: str


class TokenPair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    doit_changer_mot_de_passe: bool = False


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class MeOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    nom: str
    prenom: str
    login_id: str
    email: EmailStr | None
    role: str
    email_verifie: bool
    mot_de_passe_temporaire: bool


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ancien_mot_de_passe: str
    nouveau_mot_de_passe: str

    @field_validator("nouveau_mot_de_passe")
    @classmethod
    def _valider_force_nouveau_mot_de_passe(cls, value: str) -> str:
        if not _PASSWORD_PATTERN.match(value):
            raise ValueError(
                "Le mot de passe doit contenir au moins 8 caracteres, une majuscule et un chiffre."
            )
        return value
