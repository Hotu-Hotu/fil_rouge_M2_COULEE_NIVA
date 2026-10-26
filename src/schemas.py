"""Modele de base commun a tous les schemas de l'API."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class CustomModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_datetime(self, value):
        # toutes les dates sortent au meme format, en UTC si aucun fuseau n'est indique
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            return value.strftime("%Y-%m-%dT%H:%M:%S%z")
        return value
