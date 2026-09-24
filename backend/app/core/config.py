from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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

    casier_judiciaire_storage_path: str = "./casier-judiciaire"

    cors_allow_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
