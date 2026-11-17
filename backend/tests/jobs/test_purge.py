"""Tests de la purge : resultats dans la journee, contenu 3 a 6 mois."""

from datetime import timedelta

from conftest import auth, requires_ffmpeg, upload
from src.jobs.models import Job
from src.jobs.purge import purge_expired_data
from src.utils import utcnow

pytestmark = requires_ffmpeg


async def finished_job(client, user_key, audio, run_queue):
    job_id = (await upload(client, user_key, audio, "text")).json()["id"]
    await run_queue()
    return job_id


async def test_nothing_is_purged_before_expiry(client, user_key, sessions, audio, run_queue):
    await finished_job(client, user_key, audio, run_queue)
    async with sessions() as session:
        assert await purge_expired_data(session) == (0, 0)


async def test_results_expire_after_a_day(client, user_key, sessions, audio, run_queue, data_dir):
    job_id = await finished_job(client, user_key, audio, run_queue)
    async with sessions() as session:
        assert await purge_expired_data(session, now=utcnow() + timedelta(hours=25)) == (1, 0)

    job = (await client.get(f"/jobs/{job_id}", headers=auth(user_key))).json()
    assert job["files_expired"] is True
    download = await client.get(job["files"][0]["url"], headers=auth(user_key))
    assert download.status_code == 410
    assert not (data_dir / job_id / "output").exists()
    # le fichier recu et la transcription restent pour les data scientists
    assert (data_dir / job_id / "input.wav").exists()
    async with sessions() as session:
        assert (await session.get(Job, job_id)).transcript_text is not None


async def test_content_is_deleted_after_dataset_retention(
    client, user_key, sessions, audio, run_queue, data_dir
):
    job_id = await finished_job(client, user_key, audio, run_queue)
    async with sessions() as session:
        assert await purge_expired_data(session, now=utcnow() + timedelta(days=91)) == (1, 1)
        job = await session.get(Job, job_id)
    assert not (data_dir / job_id).exists()
    assert job.transcript_text is None
    assert job.purged_at is not None
    # la ligne reste, pour des statistiques justes
    assert job.processing_seconds is not None
