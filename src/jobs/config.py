from pydantic_settings import BaseSettings, SettingsConfigDict


class JobsConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # dossier des fichiers recus et des resultats, un sous-dossier par traitement
    DATA_DIR: str = "data"


jobs_settings = JobsConfig()
