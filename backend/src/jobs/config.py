from pydantic_settings import BaseSettings, SettingsConfigDict


class JobsConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # dossier des fichiers recus et des resultats, un sous-dossier par traitement
    DATA_DIR: str = "data"

    # worker : nom unique par worker, frequence de consultation de la file et de la purge
    WORKER_NAME: str = "worker-1"
    POLL_INTERVAL_SECONDS: float = 1.0
    PURGE_INTERVAL_SECONDS: float = 600.0

    # conservation (docs/decisions.md) : resultats disponibles dans la journee pour
    # l'utilisateur, fichier recu et transcription gardes 3 a 6 mois pour les data scientists
    USER_RETENTION_HOURS: int = 24
    DATASET_RETENTION_DAYS: int = 90


jobs_settings = JobsConfig()
