import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

_PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*\d).{8,}$")
# Borne haute : argon2 sur une entree arbitrairement longue est un vecteur de deni de service.
MOT_DE_PASSE_MAX = 128


def _valider_force(value: str) -> str:
    if not _PASSWORD_PATTERN.match(value):
        raise ValueError("Le mot de passe doit contenir au moins 8 caracteres, une majuscule et un chiffre.")
    return value


class TuteurCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nom: str = Field(min_length=1, max_length=100)
    prenom: str = Field(min_length=1, max_length=100)
    email: EmailStr
    telephone: str | None = Field(default=None, max_length=30)
    mot_de_passe: str = Field(max_length=MOT_DE_PASSE_MAX)

    @field_validator("mot_de_passe")
    @classmethod
    def _valider_force_mot_de_passe(cls, value: str) -> str:
        return _valider_force(value)


class TuteurOut(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    nom: str
    prenom: str
    email: EmailStr
    email_verifie: bool


class EnseignantCreate(TuteurCreate):
    """Memes champs et regles que TuteurCreate (voir UC-01) - creation de compte
    enseignant, prealable a UC-04 (candidature)."""


class EnseignantOut(TuteurOut):
    pass


class OtpVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    code: str = Field(max_length=12)


class RenvoiOtpRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr


class MotDePasseOublieRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifiant: str = Field(min_length=1, max_length=255)  # e-mail, ou matricule pour un eleve


class ReinitialiserMotDePasseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifiant: str = Field(min_length=1, max_length=255)
    code: str = Field(max_length=12)
    nouveau_mot_de_passe: str = Field(max_length=MOT_DE_PASSE_MAX)

    @field_validator("nouveau_mot_de_passe")
    @classmethod
    def _valider_force_nouveau(cls, value: str) -> str:
        return _valider_force(value)


class DemandeEnregistreeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str


class OtpVerifyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    email: EmailStr
    email_verifie: bool


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identifiant: str = Field(max_length=255)  # e-mail (tuteur/enseignant/admin) ou matricule (eleve)
    mot_de_passe: str = Field(max_length=MOT_DE_PASSE_MAX)


class TokenPair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    doit_changer_mot_de_passe: bool = False


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(max_length=4096)


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
    est_etudiant: bool
    telephone: str | None = None


class MiseAJourProfilRequest(BaseModel):
    """Numero Mobile Money : indispensable pour reverser un prestataire (micro-jobs) ou un
    vendeur (marketplace) - un eleve/etudiant, dont le compte est cree par l'inscription,
    n'avait aucun moyen de le renseigner."""

    model_config = ConfigDict(extra="forbid")

    telephone: str = Field(min_length=8, max_length=30)

    @field_validator("telephone")
    @classmethod
    def _valider_telephone(cls, value: str) -> str:
        valeur = value.strip()
        if not re.fullmatch(r"\+?[0-9][0-9 .-]{6,28}", valeur) or sum(c.isdigit() for c in valeur) < 8:
            raise ValueError("Numéro de téléphone invalide (ex. +229 01 97 00 00 00).")
        return valeur


class ChangePasswordOut(MeOut):
    """Le changement de mot de passe ferme toutes les autres sessions (refresh tokens
    anterieurs refuses) : la session courante recoit donc une paire de tokens neuve."""

    access_token: str
    refresh_token: str


class AdminUtilisateurOut(BaseModel):
    """UC-34/49 (lot admin ministeriel) : vue nationale, champs strictement necessaires -
    jamais mot_de_passe_hash ni casier judiciaire (voir cahier des charges, risque R2).
    `email` en `str` simple (pas `EmailStr`) : contrairement a `MeOut` (un utilisateur ne
    lit que son propre profil), cette liste agrege potentiellement des milliers de comptes
    - une seule adresse mal formee dans un jeu de donnees ancien ferait echouer (500)
    l'ecran de supervision tout entier si la validation stricte etait appliquee ici."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    nom: str
    prenom: str
    login_id: str
    email: str | None
    role: str
    actif: bool
    mot_de_passe_temporaire: bool
    created_at: datetime


class AdminUtilisateurPageOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminUtilisateurOut]
    total: int
    limit: int
    offset: int


class SuspendreCompteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif: str = Field(min_length=1)


class ReactiverCompteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motif: str | None = None


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ancien_mot_de_passe: str = Field(max_length=MOT_DE_PASSE_MAX)
    nouveau_mot_de_passe: str = Field(max_length=MOT_DE_PASSE_MAX)

    @field_validator("nouveau_mot_de_passe")
    @classmethod
    def _valider_force_nouveau_mot_de_passe(cls, value: str) -> str:
        return _valider_force(value)
