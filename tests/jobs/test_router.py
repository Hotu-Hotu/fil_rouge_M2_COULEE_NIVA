"""Tests des routes /jobs avec un faux modele."""

import asyncio

import pytest

from conftest import FailingTranscriber, requires_ffmpeg
from src.transcription.config import transcription_settings

JOB_TIMEOUT_SECONDS = 30


async def upload(client, path, output_format):
    return await client.post(
        "/jobs", files={"file": (path.name, path.read_bytes())}, data={"output_format": output_format}
    )


async def wait_for(client, job_id):
    async with asyncio.timeout(JOB_TIMEOUT_SECONDS):
        while True:
            job = (await client.get(f"/jobs/{job_id}")).json()
            if job["status"] in ("done", "failed"):
                return job
            await asyncio.sleep(0.1)


async def test_health(client):
    assert (await client.get("/health")).json() == {"status": "ok"}


@requires_ffmpeg
async def test_upload_process_and_download(client, audio):
    response = await upload(client, audio, "subtitles")
    assert response.status_code == 202
    assert response.json()["status"] in ("queued", "running", "done")

    job = await wait_for(client, response.json()["id"])
    assert job["status"] == "done"
    assert job["processing_seconds"] >= 0
    assert [f["name"] for f in job["files"]] == ["clip.en.srt", "clip.en.vtt"]

    download = await client.get(job["files"][1]["url"])
    assert download.status_code == 200
    assert download.text.startswith("WEBVTT")


@requires_ffmpeg
@pytest.mark.parametrize("transcriber", [FailingTranscriber()])
async def test_failed_processing_is_reported(client, audio):
    job = await wait_for(client, (await upload(client, audio, "text")).json()["id"])
    assert job["status"] == "failed"
    assert "out of memory" in job["error"]
    assert job["files"] == []


async def test_format_not_available_for_audio(client, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x")
    response = await upload(client, wav, "burned")
    assert response.status_code == 400
    assert "pas disponible" in response.json()["detail"]


async def test_unknown_format_is_rejected(client, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x")
    assert (await upload(client, wav, "pdf")).status_code == 422


async def test_too_large_file_is_rejected_and_cleaned(client, tmp_path, data_dir, monkeypatch):
    monkeypatch.setattr(transcription_settings, "MAX_SIZE_MB", 0)
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x" * 10)
    response = await upload(client, wav, "text")
    assert response.status_code == 413
    # aucun dossier de traitement ne doit rester
    assert list(data_dir.iterdir()) == []


async def test_unknown_job_and_file(client):
    assert (await client.get("/jobs/nope")).status_code == 404
    assert (await client.get("/jobs/nope/files/x.txt")).status_code == 404


@requires_ffmpeg
async def test_only_produced_files_can_be_downloaded(client, audio):
    job = await wait_for(client, (await upload(client, audio, "text")).json()["id"])
    assert (await client.get(f"/jobs/{job['id']}/files/input.wav")).status_code == 404
