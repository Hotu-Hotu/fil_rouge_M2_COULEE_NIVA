"""Enchainement complet : validation, transcription, puis production du format demande."""

import tempfile
from pathlib import Path

from . import formatters, media
from .config import transcription_settings
from .models import ALLOWED_FORMATS, INPUT_EXTENSIONS, InputType, OutputFormat, ProcessResult
from .transcribers import Transcriber


class InvalidRequest(ValueError):
    """Fichier ou format refuse : le message est destine a l'utilisateur."""


def detect_input_type(input_path: Path) -> InputType:
    input_type = INPUT_EXTENSIONS.get(input_path.suffix.lower())
    if input_type is None:
        accepted = ", ".join(INPUT_EXTENSIONS)
        raise InvalidRequest(f"Extension non supportee : {input_path.suffix} (acceptees : {accepted})")
    return input_type


def check_format(filename, output_format: OutputFormat):
    """Verifie l'extension et que le format demande existe pour ce type de fichier."""
    input_type = detect_input_type(Path(filename))
    if output_format not in ALLOWED_FORMATS[input_type]:
        allowed = ", ".join(sorted(f.value for f in ALLOWED_FORMATS[input_type]))
        raise InvalidRequest(
            f"Le format '{output_format.value}' n'est pas disponible pour un fichier "
            f"{input_type.value} (formats possibles : {allowed})"
        )


def check_size(size_bytes):
    """Refuse les fichiers trop gros. Renvoie un avertissement au-dela du seuil."""
    size_mb = size_bytes / 1_000_000
    if size_mb > transcription_settings.MAX_SIZE_MB:
        raise InvalidRequest(
            f"Fichier trop volumineux : {size_mb:.0f} Mo (maximum {transcription_settings.MAX_SIZE_MB} Mo)"
        )
    if size_mb > transcription_settings.WARN_SIZE_MB:
        return [f"Fichier volumineux ({size_mb:.0f} Mo) : le traitement peut etre long."]
    return []


def validate(input_path: Path, output_format: OutputFormat):
    """Verifie le fichier et le format demande. Renvoie les avertissements eventuels."""
    if not input_path.is_file():
        raise InvalidRequest(f"Fichier introuvable : {input_path}")
    check_format(input_path, output_format)
    return check_size(input_path.stat().st_size)


def process(
    input_path, output_format, output_dir, transcriber: Transcriber, output_stem=None
) -> ProcessResult:
    """`output_stem` : nom des fichiers produits (par defaut, celui du fichier d'entree)."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    output_format = OutputFormat(output_format)
    warnings = validate(input_path, output_format)
    output_dir.mkdir(parents=True, exist_ok=True)

    duration = media.get_duration(input_path)
    # l'audio extrait est un fichier intermediaire : on le met dans un dossier temporaire
    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = Path(tmp_dir) / "audio.wav"
        media.extract_audio(input_path, audio_path)
        transcription = transcriber.transcribe(audio_path, duration)

    result = ProcessResult(output_format, transcription, warnings=warnings)
    stem = output_stem or input_path.stem
    srt_path = output_dir / f"{stem}.en.srt"

    if output_format is OutputFormat.TEXT:
        text_path = output_dir / f"{stem}.txt"
        text_path.write_text(formatters.to_text(transcription.segments), encoding="utf-8")
        result.files.append(text_path)
        return result

    srt_path.write_text(formatters.to_srt(transcription.segments), encoding="utf-8")

    if output_format is OutputFormat.SUBTITLES:
        vtt_path = output_dir / f"{stem}.en.vtt"
        vtt_path.write_text(formatters.to_vtt(transcription.segments), encoding="utf-8")
        result.files += [srt_path, vtt_path]
    elif output_format is OutputFormat.TRACK:
        video_path = output_dir / f"{stem}-subtitled.mp4"
        media.add_subtitle_track(input_path, srt_path, video_path, transcription_settings.SUBTITLE_LANGUAGE)
        result.files += [video_path, srt_path]
    elif output_format is OutputFormat.BURNED:
        video_path = output_dir / f"{stem}-burned.mp4"
        media.burn_subtitles(input_path, srt_path, video_path)
        # le .srt n'a servi qu'a l'incrustation
        srt_path.unlink()
        result.files.append(video_path)
    return result
