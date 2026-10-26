"""Configuration globale de l'application (variables d'environnement ou fichier .env)."""

from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    LOCAL = "local"
    STAGING = "staging"
    PRODUCTION = "production"

    @property
    def shows_docs(self):
        return self in (Environment.LOCAL, Environment.STAGING)


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: Environment = Environment.LOCAL
    APP_VERSION: str = "0.1.0"


settings = Config()
