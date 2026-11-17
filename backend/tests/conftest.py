"""Faux modele, petits medias, base SQLite jetable et client HTTP partages par les tests.

ffmpeg tourne pour de vrai, Whisper non : les tests n'ont besoin ni de GPU ni de PostgreSQL.
"""

import shutil
import subprocess

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth.service import create_user
from src.database import get_session
from src.jobs.config import jobs_settings
from src.jobs.worker import run_next_job
from src.main import app
from src.models import Base
from src.transcription.models import Segment, Transcription
from src.transcription.transcribers import Transcriber

requires_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg absent")


class FakeTranscriber(Transcriber):
    def transcribe(self, audio_path, duration):
        segments = [Segment(0.0, 1.0, "Hello."), Segment(1.0, duration, "Goodbye.")]
        return Transcription(text="Hello. Goodbye.", segments=segments)


class FailingTranscriber(Transcriber):
    def transcribe(self, audio_path, duration):
        raise RuntimeError("CUDA out of memory")


def generate(path, video):
    """Genere un petit media de 2 s (mire + bip) avec ffmpeg."""
    inputs = ["-f", "lavfi", "-i", "sine=frequency=440:duration=2"]
    if video:
        inputs = ["-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=2"] + inputs
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-shortest", str(path)], check=True)
    return path


@pytest.fixture
def transcriber():
    return FakeTranscriber()


@pytest.fixture(scope="session")
def video(tmp_path_factory):
    return generate(tmp_path_factory.mktemp("media") / "clip.mp4", video=True)


@pytest.fixture(scope="session")
def audio(tmp_path_factory):
    return generate(tmp_path_factory.mktemp("media") / "clip.wav", video=False)


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    path = tmp_path / "data"
    monkeypatch.setattr(jobs_settings, "DATA_DIR", str(path))
    return path


@pytest.fixture
async def sessions(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def user_key(sessions):
    async with sessions() as session:
        _, api_key = await create_user(session, "Alice")
    return api_key


@pytest.fixture
async def admin_key(sessions):
    async with sessions() as session:
        _, api_key = await create_user(session, "Admin", is_admin=True)
    return api_key


@pytest.fixture
async def client(sessions):
    async def test_session():
        async with sessions() as session:
            yield session

    # l'API utilise la base de test
    app.dependency_overrides[get_session] = test_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def run_queue(sessions, transcriber):
    """Fait tourner le worker jusqu'a ce que la file soit vide."""

    async def run():
        while await run_next_job(sessions, transcriber, "test-worker"):
            pass

    return run


def auth(api_key):
    return {"X-API-Key": api_key}


async def upload(client, api_key, path, output_format):
    return await client.post(
        "/jobs",
        files={"file": (path.name, path.read_bytes())},
        data={"output_format": output_format},
        headers=auth(api_key),
    )
