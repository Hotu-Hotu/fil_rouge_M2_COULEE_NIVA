"""Worker de transcription : python -m src.jobs.worker

Processus separe de l'API : c'est le seul a charger le modele. Il prend les traitements en
attente dans la base, un par un. Pour plusieurs GPU, lancer un worker par GPU, chacun avec
son propre WORKER_NAME (et CUDA_VISIBLE_DEVICES).
"""

import asyncio
import logging
import time
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker

from src.database import engine, session_factory
from src.jobs.config import jobs_settings
from src.jobs.constants import JobStatus
from src.jobs.purge import purge_expired_data
from src.jobs.service import claim_next_job, fail_interrupted_jobs
from src.jobs.utils import input_path, output_dir
from src.transcription.config import transcription_settings
from src.transcription.pipeline import process
from src.transcription.transcribers import Transcriber, get_transcriber
from src.utils import utcnow

logger = logging.getLogger("worker")


async def run_next_job(sessions: async_sessionmaker, transcriber: Transcriber, worker_name) -> bool:
    """Traite le prochain traitement en attente. Renvoie False si la file est vide."""
    async with sessions() as session:
        job = await claim_next_job(session, worker_name)
        if job is None:
            return False

        logger.info("Traitement %s (%s, %s)", job.id, job.filename, job.output_format)
        start = time.perf_counter()
        try:
            # le calcul est bloquant : il tourne dans un thread pour ne pas figer la boucle
            result = await asyncio.to_thread(
                process,
                input_path(job.id, job.filename),
                job.output_format,
                output_dir(job.id),
                transcriber,
                output_stem=Path(job.filename).stem,
            )
        except Exception as error:
            logger.exception("Echec du traitement %s", job.id)
            job.status = JobStatus.FAILED
            job.error = str(error) or type(error).__name__
        else:
            job.status = JobStatus.DONE
            job.files = [path.name for path in result.files]
            job.warnings = [*job.warnings, *result.warnings]
            job.transcript_text = result.transcription.text
            job.media_seconds = result.media_seconds
        job.processing_seconds = time.perf_counter() - start
        job.finished_at = utcnow()
        await session.commit()
        logger.info("Traitement %s : %s en %.1f s", job.id, job.status, job.processing_seconds)
        return True


async def run_worker(sessions: async_sessionmaker, transcriber: Transcriber, worker_name):
    async with sessions() as session:
        interrupted = await fail_interrupted_jobs(session, worker_name)
    if interrupted:
        logger.warning("%d traitement(s) interrompu(s) par le dernier arret, marques en echec", interrupted)

    last_purge = float("-inf")
    while True:
        if time.monotonic() - last_purge >= jobs_settings.PURGE_INTERVAL_SECONDS:
            async with sessions() as session:
                expired, purged = await purge_expired_data(session)
            if expired or purged:
                logger.info("Purge : %d resultat(s) expire(s), %d traitement(s) supprime(s)", expired, purged)
            last_purge = time.monotonic()

        if not await run_next_job(sessions, transcriber, worker_name):
            await asyncio.sleep(jobs_settings.POLL_INTERVAL_SECONDS)


async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s : %(message)s")
    logger.info("Chargement du modele %s", transcription_settings.MODEL_NAME)
    transcriber = await asyncio.to_thread(
        get_transcriber, transcription_settings.TRANSCRIBER, transcription_settings.MODEL_NAME
    )
    logger.info("Worker %s pret", jobs_settings.WORKER_NAME)
    try:
        await run_worker(session_factory, transcriber, jobs_settings.WORKER_NAME)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker arrete")
