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


class NotFound(DetailedHTTPException):
    STATUS_CODE = status.HTTP_404_NOT_FOUND


class PayloadTooLarge(DetailedHTTPException):
    STATUS_CODE = status.HTTP_413_CONTENT_TOO_LARGE
    DETAIL = "Fichier trop volumineux"
