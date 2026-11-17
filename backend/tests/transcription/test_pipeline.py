"""Tests du pipeline complet avec un faux modele : ffmpeg tourne pour de vrai, Whisper non."""

import ffmpeg
import pytest

from conftest import requires_ffmpeg
from src.transcription.config import transcription_settings
from src.transcription.models import OutputFormat
from src.transcription.pipeline import InvalidRequest, process

pytestmark = requires_ffmpeg


def streams(path):
    return sorted(s["codec_type"] for s in ffmpeg.probe(str(path))["streams"])


def test_text(audio, tmp_path, transcriber):
    result = process(audio, "text", tmp_path, transcriber)
    assert [p.name for p in result.files] == ["clip.txt"]
    assert result.files[0].read_text(encoding="utf-8") == "Hello. Goodbye.\n"


def test_subtitles(audio, tmp_path, transcriber):
    result = process(audio, "subtitles", tmp_path, transcriber)
    assert [p.name for p in result.files] == ["clip.en.srt", "clip.en.vtt"]
    assert result.files[1].read_text(encoding="utf-8").startswith("WEBVTT")


def test_output_stem(audio, tmp_path, transcriber):
    result = process(audio, "text", tmp_path, transcriber, output_stem="meeting")
    assert [p.name for p in result.files] == ["meeting.txt"]


def test_track(video, tmp_path, transcriber):
    result = process(video, "track", tmp_path, transcriber)
    subtitled, srt = result.files
    assert srt.name == "clip.en.srt"
    assert streams(subtitled) == ["audio", "subtitle", "video"]
    subtitle = next(s for s in ffmpeg.probe(str(subtitled))["streams"] if s["codec_type"] == "subtitle")
    assert subtitle["disposition"]["default"] == 1
    assert subtitle["tags"]["language"] == "eng"


def test_burned(video, tmp_path, transcriber):
    result = process(video, OutputFormat.BURNED, tmp_path, transcriber)
    assert [p.name for p in result.files] == ["clip-burned.mp4"]
    # sous-titres dessines dans l'image : pas de piste de sous-titres
    assert streams(result.files[0]) == ["audio", "video"]
    assert not (tmp_path / "clip.en.srt").exists()


@pytest.mark.parametrize("output_format", ["burned", "track"])
def test_audio_cannot_produce_video(audio, tmp_path, transcriber, output_format):
    with pytest.raises(InvalidRequest, match="pas disponible"):
        process(audio, output_format, tmp_path, transcriber)


def test_unsupported_extension(tmp_path, transcriber):
    other = tmp_path / "clip.avi"
    other.write_bytes(b"x")
    with pytest.raises(InvalidRequest, match="Extension non supportee"):
        process(other, "text", tmp_path, transcriber)


def test_missing_file(tmp_path, transcriber):
    with pytest.raises(InvalidRequest, match="introuvable"):
        process(tmp_path / "absent.mp4", "text", tmp_path, transcriber)


def test_size_limits(audio, tmp_path, transcriber, monkeypatch):
    monkeypatch.setattr(transcription_settings, "WARN_SIZE_MB", 0)
    result = process(audio, "text", tmp_path, transcriber)
    assert result.warnings and "volumineux" in result.warnings[0]

    monkeypatch.setattr(transcription_settings, "MAX_SIZE_MB", 0)
    with pytest.raises(InvalidRequest, match="trop volumineux"):
        process(audio, "text", tmp_path, transcriber)
