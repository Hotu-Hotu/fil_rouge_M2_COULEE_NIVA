"""Reglages du pipeline de transcription (variables d'environnement ou fichier .env)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class TranscriptionConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Modele de transcription : anglais uniquement pour l'instant (voir docs/decisions.md)
    TRANSCRIBER: str = "whisper"
    MODEL_NAME: str = "openai/whisper-medium.en"
    SUBTITLE_LANGUAGE: str = "eng"

    # Taille des fichiers soumis, en Mo. Valeurs provisoires, a ajuster apres le test de charge.
    WARN_SIZE_MB: int = 500
    MAX_SIZE_MB: int = 2000


transcription_settings = TranscriptionConfig()
