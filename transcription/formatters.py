"""Mise en forme d'une transcription : SRT, WebVTT et texte brut."""

from .models import Segment


def format_time(seconds, separator=","):
    """Formate un temps en secondes : HH:MM:SS,mmm (SRT) ou HH:MM:SS.mmm (VTT)."""
    # on travaille en millisecondes entieres pour eviter les arrondis du type 59,9996 -> 59,1000
    total_ms = round(seconds * 1000)
    hours, total_ms = divmod(total_ms, 3_600_000)
    minutes, total_ms = divmod(total_ms, 60_000)
    secs, milliseconds = divmod(total_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{milliseconds:03d}"


def _cue_text(segment: Segment):
    if segment.speaker:
        return f"[{segment.speaker}] {segment.text}"
    return segment.text


def to_srt(segments: list[Segment]):
    blocks = []
    for number, segment in enumerate(segments, start=1):
        timing = f"{format_time(segment.start)} --> {format_time(segment.end)}"
        blocks.append(f"{number}\n{timing}\n{_cue_text(segment)}\n")
    return "\n".join(blocks)


def to_vtt(segments: list[Segment]):
    blocks = ["WEBVTT\n"]
    for segment in segments:
        timing = f"{format_time(segment.start, '.')} --> {format_time(segment.end, '.')}"
        blocks.append(f"{timing}\n{_cue_text(segment)}\n")
    return "\n".join(blocks)


def to_text(segments: list[Segment]):
    """Texte sans timestamp. Un changement de locuteur ouvre un nouveau paragraphe."""
    paragraphs = []
    current_speaker = object()
    for segment in segments:
        if segment.speaker != current_speaker:
            current_speaker = segment.speaker
            prefix = f"{segment.speaker} : " if segment.speaker else ""
            paragraphs.append(prefix + segment.text)
        else:
            paragraphs[-1] += " " + segment.text
    return "\n\n".join(paragraphs) + "\n"
