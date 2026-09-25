import secrets
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[3] = racine du depot (a cote de .env.example)
_REPO_ROOT_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_REPO_ROOT_ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    environment: str = "development"

    database_url: str = "postgresql+psycopg://user:password@localhost:5432/luluschools"

    jwt_secret_key: str = "change-me"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    freellm_base_url: str = "https://freellm-lucio.onrender.com/v1"
    freellm_api_key: str = ""

    lulufiles_base_url: str = "https://lulufiles-api.onrender.com"
    lulufiles_api_key: str = ""

    kkiapay_public_key: str = ""
    kkiapay_private_key: str = ""
    kkiapay_secret: str = ""
    kkiapay_sandbox: bool = True

    brevo_api_key: str = ""
    brevo_sender_email: str = "no-reply@luluschools.example"
    brevo_sender_name: str = "LuluSchools"

    # Secret chiffrant le contenu du casier judiciaire stocke en base (voir
    # app/core/crypto.py, VerificationCasierJudiciaire.contenu_chiffre) - jamais
    # commite, genere par Render (generateValue: true) en production. Le
    # default_factory tire une valeur aleatoire differente a chaque demarrage en
    # dev/tests (jamais la meme valeur committee ici).
    casier_judiciaire_encryption_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))

    cors_allow_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
