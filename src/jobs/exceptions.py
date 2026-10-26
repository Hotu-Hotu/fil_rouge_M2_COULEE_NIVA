from src.exceptions import NotFound


class JobNotFound(NotFound):
    DETAIL = "Traitement introuvable"


class JobFileNotFound(NotFound):
    DETAIL = "Fichier introuvable"
