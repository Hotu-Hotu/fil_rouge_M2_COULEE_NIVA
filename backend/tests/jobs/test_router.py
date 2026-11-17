"""Tests des routes /jobs : l'API met en file, le worker de test execute."""

import pytest

from conftest import FailingTranscriber, auth, requires_ffmpeg, upload
from src.transcription.config import transcription_settings


async def test_health(client):
    assert (await client.get("/health")).json() == {"status": "ok"}


@requires_ffmpeg
async def test_upload_process_and_download(client, user_key, audio, run_queue):
    response = await upload(client, user_key, audio, "subtitles")
    assert response.status_code == 202
    job = response.json()
    assert job["status"] == "queued"

    await run_queue()

    job = (await client.get(f"/jobs/{job['id']}", headers=auth(user_key))).json()
    assert job["status"] == "done"
    assert job["media_seconds"] == pytest.approx(2, abs=0.1)
    assert job["processing_seconds"] >= 0
    assert [f["name"] for f in job["files"]] == ["clip.en.srt", "clip.en.vtt"]

    download = await client.get(job["files"][1]["url"], headers=auth(user_key))
    assert download.status_code == 200
    assert download.text.startswith("WEBVTT")


@requires_ffmpeg
@pytest.mark.parametrize("transcriber", [FailingTranscriber()])
async def test_failed_processing_is_reported(client, user_key, audio, run_queue):
    job_id = (await upload(client, user_key, audio, "text")).json()["id"]
    await run_queue()
    job = (await client.get(f"/jobs/{job_id}", headers=auth(user_key))).json()
    assert job["status"] == "failed"
    assert "out of memory" in job["error"]
    assert job["files"] == []


async def test_list_only_my_jobs(client, user_key, admin_key, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x")
    await upload(client, user_key, wav, "text")
    await upload(client, admin_key, wav, "text")
    jobs = (await client.get("/jobs", headers=auth(user_key))).json()
    assert len(jobs) == 1


async def test_other_users_jobs_are_invisible(client, user_key, admin_key, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x")
    job_id = (await upload(client, admin_key, wav, "text")).json()["id"]
    assert (await client.get(f"/jobs/{job_id}", headers=auth(user_key))).status_code == 404


async def test_format_not_available_for_audio(client, user_key, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x")
    response = await upload(client, user_key, wav, "burned")
    assert response.status_code == 400
    assert "pas disponible" in response.json()["detail"]


async def test_unknown_format_is_rejected(client, user_key, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x")
    assert (await upload(client, user_key, wav, "pdf")).status_code == 422


async def test_too_large_file_is_rejected_and_cleaned(client, user_key, tmp_path, data_dir, monkeypatch):
    monkeypatch.setattr(transcription_settings, "MAX_SIZE_MB", 0)
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x" * 10)
    response = await upload(client, user_key, wav, "text")
    assert response.status_code == 413
    # ni dossier ni traitement ne doivent rester
    assert list(data_dir.iterdir()) == []
    assert (await client.get("/jobs", headers=auth(user_key))).json() == []


async def test_unknown_job_and_file(client, user_key):
    assert (await client.get("/jobs/nope", headers=auth(user_key))).status_code == 404
    assert (await client.get("/jobs/nope/files/x.txt", headers=auth(user_key))).status_code == 404


@requires_ffmpeg
async def test_only_produced_files_can_be_downloaded(client, user_key, audio, run_queue):
    job_id = (await upload(client, user_key, audio, "text")).json()["id"]
    await run_queue()
    response = await client.get(f"/jobs/{job_id}/files/input.wav", headers=auth(user_key))
    assert response.status_code == 404
