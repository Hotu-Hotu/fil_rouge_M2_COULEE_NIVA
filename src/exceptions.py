"""Exceptions HTTP communes : chaque domaine en derive ses erreurs avec un message clair."""

from fastapi import HTTPException, status


class DetailedHTTPException(HTTPException):
    STATUS_CODE = status.HTTP_500_INTERNAL_SERVER_ERROR
    DETAIL = "Erreur interne du serveur"

    def __init__(self, detail: str | None = None):
        super().__init__(status_code=self.STATUS_CODE, detail=detail or self.DETAIL)


class BadRequest(DetailedHTTPException):
    STATUS_CODE = status.HTTP_400_BAD_REQUEST
    DETAIL = "Requete invalide"


class NotAuthenticated(DetailedHTTPException):
    STATUS_CODE = status.HTTP_401_UNAUTHORIZED
    DETAIL = "Cle d'API absente ou invalide"

    def __init__(self, detail: str | None = None):
        super().__init__(detail)
        self.headers = {"WWW-Authenticate": "ApiKey"}


class PermissionDenied(DetailedHTTPException):
    STATUS_CODE = status.HTTP_403_FORBIDDEN
    DETAIL = "Acces reserve aux administrateurs"


class NotFound(DetailedHTTPException):
    STATUS_CODE = status.HTTP_404_NOT_FOUND


class Gone(DetailedHTTPException):
    STATUS_CODE = status.HTTP_410_GONE
    DETAIL = "Donnees supprimees a l'expiration de leur duree de conservation"


class PayloadTooLarge(DetailedHTTPException):
    STATUS_CODE = status.HTTP_413_CONTENT_TOO_LARGE
    DETAIL = "Fichier trop volumineux"
