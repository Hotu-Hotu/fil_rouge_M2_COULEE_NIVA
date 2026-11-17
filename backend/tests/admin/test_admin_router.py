"""Tests des routes /admin : statistiques, liste des traitements, acces au contenu trace."""

import pytest

from conftest import FailingTranscriber, auth, requires_ffmpeg, upload

ACCESS_REQUEST = {"reason": "Plainte d'un utilisateur, verification", "legal_reference": "FORM-2026-001"}


async def test_stats_when_empty(client, admin_key):
    stats = (await client.get("/admin/stats", headers=auth(admin_key))).json()
    assert stats["total"] == 0
    assert stats["average_processing_seconds"] is None
    assert set(stats["by_format"]) == {"burned", "track", "subtitles", "text"}


@requires_ffmpeg
async def test_stats_count_by_status_and_format(client, user_key, admin_key, audio, run_queue, tmp_path):
    await upload(client, user_key, audio, "text")
    await upload(client, user_key, audio, "subtitles")
    await run_queue()
    # un traitement encore en attente
    await upload(client, user_key, audio, "text")

    stats = (await client.get("/admin/stats", headers=auth(admin_key))).json()
    assert (stats["total"], stats["done"], stats["failed"], stats["unfinished"]) == (3, 2, 0, 1)
    assert stats["average_processing_seconds"] >= 0
    assert stats["realtime_factor"] >= 0
    text = stats["by_format"]["text"]
    assert (text["total"], text["done"], text["unfinished"]) == (2, 1, 1)
    assert stats["by_format"]["burned"]["total"] == 0


@requires_ffmpeg
@pytest.mark.parametrize("transcriber", [FailingTranscriber()])
async def test_stats_count_failures(client, user_key, admin_key, audio, run_queue):
    await upload(client, user_key, audio, "text")
    await run_queue()
    stats = (await client.get("/admin/stats", headers=auth(admin_key))).json()
    assert stats["failed"] == 1
    assert stats["by_format"]["text"]["failed"] == 1
    assert stats["average_processing_seconds"] is None


async def test_admin_sees_who_did_what_without_content(client, user_key, admin_key, tmp_path):
    wav = tmp_path / "meeting.wav"
    wav.write_bytes(b"x")
    await upload(client, user_key, wav, "text")
    jobs = (await client.get("/admin/jobs", headers=auth(admin_key))).json()
    assert len(jobs) == 1
    assert jobs[0]["user"]["name"] == "Alice"
    assert jobs[0]["filename"] == "meeting.wav"
    assert "transcript_text" not in jobs[0]

    filtered = await client.get("/admin/jobs", params={"status": "done"}, headers=auth(admin_key))
    assert filtered.json() == []


@requires_ffmpeg
async def test_content_access_requires_a_reason_and_is_logged(client, user_key, admin_key, audio, run_queue):
    job_id = (await upload(client, user_key, audio, "text")).json()["id"]
    await run_queue()
    url = f"/admin/jobs/{job_id}/content"

    assert (await client.post(url, headers=auth(admin_key), json={})).status_code == 422
    too_short = {"reason": "test", "legal_reference": "F1"}
    assert (await client.post(url, headers=auth(admin_key), json=too_short)).status_code == 422

    response = await client.post(url, headers=auth(admin_key), json=ACCESS_REQUEST)
    assert response.status_code == 200
    assert response.json()["transcript_text"] == "Hello. Goodbye."

    log = (await client.get("/admin/content-accesses", headers=auth(admin_key))).json()
    assert len(log) == 1
    assert log[0]["job_id"] == job_id
    assert log[0]["admin"]["name"] == "Admin"
    assert log[0]["legal_reference"] == "FORM-2026-001"


async def test_content_of_unfinished_job_is_unavailable(client, user_key, admin_key, tmp_path):
    wav = tmp_path / "clip.wav"
    wav.write_bytes(b"x")
    job_id = (await upload(client, user_key, wav, "text")).json()["id"]
    url = f"/admin/jobs/{job_id}/content"
    assert (await client.post(url, headers=auth(admin_key), json=ACCESS_REQUEST)).status_code == 410
    assert (
        await client.post("/admin/jobs/nope/content", headers=auth(admin_key), json=ACCESS_REQUEST)
    ).status_code == 404
    # rien n'est journalise quand le contenu n'est pas donne
    assert (await client.get("/admin/content-accesses", headers=auth(admin_key))).json() == []
