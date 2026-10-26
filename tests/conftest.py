"""Faux modele, petits medias et client HTTP partages par les tests.

ffmpeg tourne pour de vrai, Whisper non : les tests n'ont pas besoin de GPU.
"""

import shutil
import subprocess

import pytest
from httpx import ASGITransport, AsyncClient

from src.jobs.dependencies import get_queue
from src.jobs.service import JobQueue
from src.main import app
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


@pytest.fixture
def data_dir(tmp_path):
    return tmp_path / "data"


@pytest.fixture
def queue(transcriber, data_dir):
    job_queue = JobQueue(transcriber, data_dir)
    yield job_queue
    job_queue.shutdown()


@pytest.fixture
async def client(queue):
    # l'API utilise la file de test : pas de chargement du vrai modele
    app.dependency_overrides[get_queue] = lambda: queue
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
