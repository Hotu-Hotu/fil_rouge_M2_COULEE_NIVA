"""Reglages du pipeline. Les valeurs peuvent etre surchargees par variables d'environnement."""

import os

# Modele de transcription : anglais uniquement pour l'instant (voir docs/decisions.md)
TRANSCRIBER = os.getenv("TRANSCRIBER", "whisper")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/whisper-medium.en")
SUBTITLE_LANGUAGE = os.getenv("SUBTITLE_LANGUAGE", "eng")

# Taille des fichiers soumis, en Mo. Valeurs provisoires, a ajuster apres le test de charge.
WARN_SIZE_MB = int(os.getenv("WARN_SIZE_MB", "500"))
MAX_SIZE_MB = int(os.getenv("MAX_SIZE_MB", "2000"))
