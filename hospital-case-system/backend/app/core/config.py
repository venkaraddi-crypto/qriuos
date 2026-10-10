from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_KEY = "dev-secret-change-me"
MIN_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///./hospital.db"
    SECRET_KEY: str = DEV_SECRET_KEY
    FIELD_ENCRYPTION_KEY: str | None = None
    ENVIRONMENT: str = "development"
    MAX_DOCUMENT_BYTES: int = 15 * 1024 * 1024
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    # Swap this base URL (and add credentials) to move the ABHA bridge from
    # mock to the real ABDM sandbox — request/response shapes already match.
    ABDM_BASE_URL: str = "mock://abdm"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    # Sarvam AI is the primary engine for every AI capability. An
    # admin-configured key in AI Settings overrides this per capability.
    SARVAM_API_KEY: str | None = None
    SARVAM_STT_MODEL: str = "saaras:v3"
    SARVAM_STT_LANGUAGE: str = "unknown"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    def validate_for_environment(self) -> None:
        if not self.is_production:
            return
        if self.SECRET_KEY == DEV_SECRET_KEY or len(self.SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
            raise RuntimeError(
                "SECRET_KEY must be set to a strong value "
                f"(>= {MIN_SECRET_KEY_LENGTH} chars) in production"
            )
        if not self.FIELD_ENCRYPTION_KEY:
            raise RuntimeError("FIELD_ENCRYPTION_KEY must be set in production")


settings = Settings()
settings.validate_for_environment()
