"""Structures de donnees partagees par les modules du pipeline."""

from dataclasses import dataclass, field
from enum import StrEnum


class InputType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"


class OutputFormat(StrEnum):
    BURNED = "burned"  # video avec sous-titres dessines sur l'image
    TRACK = "track"  # video avec piste de sous-titres activable + .srt a cote
    SUBTITLES = "subtitles"  # .srt + .vtt (apercu navigateur)
    TEXT = "text"  # .txt sans timestamp


INPUT_EXTENSIONS = {".mp4": InputType.VIDEO, ".wav": InputType.AUDIO}

ALLOWED_FORMATS = {
    InputType.VIDEO: set(OutputFormat),
    InputType.AUDIO: {OutputFormat.SUBTITLES, OutputFormat.TEXT},
}


@dataclass
class Segment:
    """Un morceau de transcription avec ses bornes en secondes."""

    start: float
    end: float
    text: str
    # rempli par un futur modele d'identification du locuteur
    speaker: str | None = None


@dataclass
class Transcription:
    text: str
    segments: list[Segment]


@dataclass
class ProcessResult:
    output_format: OutputFormat
    transcription: Transcription
    files: list = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
