"""Traitements et file d'attente.

Version simple : les traitements sont gardes en memoire et executes un par un dans
un thread dedie, puisqu'il n'y a qu'un GPU. Ils seront persistes en base (etape 2b)
puis confies a une vraie file de taches (etape 2c).
"""

import shutil
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from src.jobs.constants import JobStatus
from src.jobs.schemas import JobFile, JobResponse
from src.transcription.models import OutputFormat
from src.transcription.pipeline import process
from src.transcription.transcribers import Transcriber


def now():
    return datetime.now(UTC)


@dataclass
class Job:
    id: str
    filename: str
    output_format: OutputFormat
    input_path: Path
    output_dir: Path
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=now)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    files: list[str] = field(default_factory=list)

    @property
    def processing_seconds(self):
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def to_response(self) -> JobResponse:
        return JobResponse(
            id=self.id,
            filename=self.filename,
            output_format=self.output_format,
            status=self.status,
            created_at=self.created_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            processing_seconds=self.processing_seconds,
            warnings=self.warnings,
            error=self.error,
            files=[JobFile(name=name, url=f"/jobs/{self.id}/files/{name}") for name in self.files],
        )


class JobQueue:
    def __init__(self, transcriber: Transcriber, data_dir):
        self._transcriber = transcriber
        self._data_dir = Path(data_dir)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        # un seul worker : les traitements partagent le meme GPU
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="transcription")

    def new_job(self, filename, output_format: OutputFormat) -> Job:
        """Cree le traitement et son dossier. Le fichier recu doit etre ecrit dans job.input_path."""
        job_id = uuid.uuid4().hex
        job_dir = self._data_dir / job_id
        job_dir.mkdir(parents=True)
        # on ne garde que l'extension du nom fourni par l'utilisateur
        input_path = job_dir / f"input{Path(filename).suffix.lower()}"
        job = Job(job_id, filename, output_format, input_path, job_dir / "output")
        with self._lock:
            self._jobs[job_id] = job
        return job

    def discard(self, job: Job):
        """Abandonne un traitement jamais soumis (fichier refuse) et supprime son dossier."""
        with self._lock:
            self._jobs.pop(job.id, None)
        shutil.rmtree(job.input_path.parent, ignore_errors=True)

    def submit(self, job: Job):
        self._executor.submit(self._run, job)

    def get(self, job_id) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _run(self, job: Job):
        job.status, job.started_at = JobStatus.RUNNING, now()
        try:
            # les resultats portent le nom du fichier envoye, pas "input"
            result = process(
                job.input_path,
                job.output_format,
                job.output_dir,
                self._transcriber,
                output_stem=Path(job.filename).stem,
            )
            job.files = [path.name for path in result.files]
            job.warnings += result.warnings
            job.status = JobStatus.DONE
        except Exception as error:
            traceback.print_exc()
            job.error = str(error) or type(error).__name__
            job.status = JobStatus.FAILED
        finally:
            job.finished_at = now()

    def shutdown(self):
        self._executor.shutdown(wait=False, cancel_futures=True)
