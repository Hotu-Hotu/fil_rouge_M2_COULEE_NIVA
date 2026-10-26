"""Tests du pipeline complet avec un faux modele : ffmpeg tourne pour de vrai, Whisper non."""

import shutil
import subprocess

import ffmpeg
import pytest

from transcription import config
from transcription.models import OutputFormat, Segment, Transcription
from transcription.pipeline import InvalidRequest, process
from transcription.transcribers import Transcriber

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg absent")


class FakeTranscriber(Transcriber):
    def transcribe(self, audio_path, duration):
        segments = [Segment(0.0, 1.0, "Hello."), Segment(1.0, duration, "Goodbye.")]
        return Transcription(text="Hello. Goodbye.", segments=segments)


def generate(path, video):
    """Genere un petit media de 2 s (mire + bip) avec ffmpeg."""
    inputs = ["-f", "lavfi", "-i", "sine=frequency=440:duration=2"]
    if video:
        inputs = ["-f", "lavfi", "-i", "testsrc=size=160x120:rate=10:duration=2"] + inputs
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-shortest", str(path)], check=True)
    return path


@pytest.fixture(scope="module")
def video(tmp_path_factory):
    return generate(tmp_path_factory.mktemp("media") / "clip.mp4", video=True)


@pytest.fixture(scope="module")
def audio(tmp_path_factory):
    return generate(tmp_path_factory.mktemp("media") / "clip.wav", video=False)


def streams(path):
    return sorted(s["codec_type"] for s in ffmpeg.probe(str(path))["streams"])


def test_text(audio, tmp_path):
    result = process(audio, "text", tmp_path, FakeTranscriber())
    assert [p.name for p in result.files] == ["clip.txt"]
    assert result.files[0].read_text(encoding="utf-8") == "Hello. Goodbye.\n"


def test_subtitles(audio, tmp_path):
    result = process(audio, "subtitles", tmp_path, FakeTranscriber())
    assert [p.name for p in result.files] == ["clip.en.srt", "clip.en.vtt"]
    assert result.files[1].read_text(encoding="utf-8").startswith("WEBVTT")


def test_track(video, tmp_path):
    result = process(video, "track", tmp_path, FakeTranscriber())
    subtitled, srt = result.files
    assert srt.name == "clip.en.srt"
    assert streams(subtitled) == ["audio", "subtitle", "video"]
    subtitle = next(s for s in ffmpeg.probe(str(subtitled))["streams"] if s["codec_type"] == "subtitle")
    assert subtitle["disposition"]["default"] == 1
    assert subtitle["tags"]["language"] == "eng"


def test_burned(video, tmp_path):
    result = process(video, OutputFormat.BURNED, tmp_path, FakeTranscriber())
    assert [p.name for p in result.files] == ["clip-burned.mp4"]
    # sous-titres dessines dans l'image : pas de piste de sous-titres
    assert streams(result.files[0]) == ["audio", "video"]
    assert not (tmp_path / "clip.en.srt").exists()


@pytest.mark.parametrize("output_format", ["burned", "track"])
def test_audio_cannot_produce_video(audio, tmp_path, output_format):
    with pytest.raises(InvalidRequest, match="pas disponible"):
        process(audio, output_format, tmp_path, FakeTranscriber())


def test_unsupported_extension(tmp_path):
    other = tmp_path / "clip.avi"
    other.write_bytes(b"x")
    with pytest.raises(InvalidRequest, match="Extension non supportee"):
        process(other, "text", tmp_path, FakeTranscriber())


def test_missing_file(tmp_path):
    with pytest.raises(InvalidRequest, match="introuvable"):
        process(tmp_path / "absent.mp4", "text", tmp_path, FakeTranscriber())


def test_size_limits(audio, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "WARN_SIZE_MB", 0)
    result = process(audio, "text", tmp_path, FakeTranscriber())
    assert result.warnings and "volumineux" in result.warnings[0]

    monkeypatch.setattr(config, "MAX_SIZE_MB", 0)
    with pytest.raises(InvalidRequest, match="trop volumineux"):
        process(audio, "text", tmp_path, FakeTranscriber())
