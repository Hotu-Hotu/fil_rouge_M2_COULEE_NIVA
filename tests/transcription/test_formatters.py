from src.transcription.formatters import format_time, to_srt, to_text, to_vtt
from src.transcription.models import Segment
from src.transcription.transcribers import chunks_to_segments

SEGMENTS = [Segment(0.0, 1.5, "Hello there."), Segment(1.5, 3.25, "General Kenobi.")]


def test_format_time_srt_and_vtt():
    assert format_time(0) == "00:00:00,000"
    assert format_time(3725.5) == "01:02:05,500"
    assert format_time(3725.5, ".") == "01:02:05.500"


def test_format_time_rounds_without_overflow():
    # 59,9996 s ne doit pas donner 00:00:59,1000
    assert format_time(59.9996) == "00:01:00,000"


def test_to_srt():
    assert to_srt(SEGMENTS) == (
        "1\n00:00:00,000 --> 00:00:01,500\nHello there.\n\n"
        "2\n00:00:01,500 --> 00:00:03,250\nGeneral Kenobi.\n"
    )


def test_to_vtt():
    vtt = to_vtt(SEGMENTS)
    assert vtt.startswith("WEBVTT\n")
    assert "00:00:01.500 --> 00:00:03.250\nGeneral Kenobi." in vtt


def test_to_text_has_no_timestamp():
    assert to_text(SEGMENTS) == "Hello there. General Kenobi.\n"


def test_speaker_is_shown_when_known():
    segments = [Segment(0, 1, "Hi.", "A"), Segment(1, 2, "How are you?", "A"), Segment(2, 3, "Fine.", "B")]
    assert to_text(segments) == "A : Hi. How are you?\n\nB : Fine.\n"
    assert "[B] Fine." in to_srt(segments)


def test_chunks_to_segments_cleans_whisper_output():
    chunks = [
        {"text": " First.", "timestamp": (0.0, 2.0)},
        {"text": "   ", "timestamp": (2.0, 3.0)},  # vide : ignore
        {"text": "Bad.", "timestamp": (5.0, 4.0)},  # fin avant debut : ignore
        {"text": "Last.", "timestamp": (6.0, None)},  # pas de fin : fin du media
    ]
    segments = chunks_to_segments(chunks, duration=8.0)
    assert [(s.start, s.end, s.text) for s in segments] == [(0.0, 2.0, "First."), (6.0, 8.0, "Last.")]
