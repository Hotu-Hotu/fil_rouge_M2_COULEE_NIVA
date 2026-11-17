"""Emplacement des fichiers d'un traitement : DATA_DIR/<id>/input.<ext> et DATA_DIR/<id>/output/."""

from pathlib import Path

from src.jobs.config import jobs_settings


def job_dir(job_id: str) -> Path:
    return Path(jobs_settings.DATA_DIR) / job_id


def input_path(job_id: str, filename: str) -> Path:
    # on ne garde que l'extension du nom fourni par l'utilisateur
    return job_dir(job_id) / f"input{Path(filename).suffix.lower()}"


def output_dir(job_id: str) -> Path:
    return job_dir(job_id) / "output"
