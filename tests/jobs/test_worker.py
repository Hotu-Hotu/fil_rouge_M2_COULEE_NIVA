"""Tests de la file en base et du worker."""

from conftest import requires_ffmpeg, upload
from src.jobs.constants import JobStatus
from src.jobs.models import Job
from src.jobs.service import claim_next_job, fail_interrupted_jobs
from src.jobs.worker import run_next_job


async def test_empty_queue(sessions, transcriber):
    assert await run_next_job(sessions, transcriber, "w") is False


async def test_jobs_are_claimed_oldest_first_and_only_once(client, user_key, sessions, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x")
    first = (await upload(client, user_key, wav, "text")).json()["id"]
    second = (await upload(client, user_key, wav, "text")).json()["id"]

    async with sessions() as session:
        assert (await claim_next_job(session, "w1")).id == first
        assert (await claim_next_job(session, "w2")).id == second
        # tout est pris : un troisieme worker ne recupere rien
        assert await claim_next_job(session, "w3") is None


async def test_restarted_worker_fails_its_interrupted_jobs(client, user_key, sessions, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x")
    job_id = (await upload(client, user_key, wav, "text")).json()["id"]
    async with sessions() as session:
        await claim_next_job(session, "w1")
        # un autre worker ne touche pas aux traitements de w1
        assert await fail_interrupted_jobs(session, "w2") == 0
        assert await fail_interrupted_jobs(session, "w1") == 1
        job = await session.get(Job, job_id, populate_existing=True)
    assert job.status == JobStatus.FAILED
    assert "interrompu" in job.error


@requires_ffmpeg
async def test_worker_stores_transcript_and_measures(client, user_key, sessions, audio, run_queue):
    job_id = (await upload(client, user_key, audio, "text")).json()["id"]
    await run_queue()
    async with sessions() as session:
        job = await session.get(Job, job_id)
    assert job.transcript_text == "Hello. Goodbye."
    assert job.worker_name == "test-worker"
    assert job.processing_seconds >= 0
