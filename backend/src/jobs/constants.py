from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# taille des morceaux lus lors de la reception d'un fichier
UPLOAD_CHUNK_SIZE = 1024 * 1024
