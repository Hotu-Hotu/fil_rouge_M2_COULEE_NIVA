from src.exceptions import Gone, NotFound


class JobNotFound(NotFound):
    DETAIL = "Traitement introuvable"


class JobFileNotFound(NotFound):
    DETAIL = "Fichier introuvable"


class JobFilesExpired(Gone):
    DETAIL = "Les resultats ne sont gardes que dans la journee : relancez le traitement"
