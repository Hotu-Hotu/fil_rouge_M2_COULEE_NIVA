"""Operations ffmpeg : extraction de l'audio, ajout ou incrustation des sous-titres."""

import sys
from pathlib import Path

import ffmpeg


def run_ffmpeg(stream):
    """Lance ffmpeg sans polluer la console, et affiche son erreur s'il echoue."""
    try:
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
    except ffmpeg.Error as error:
        print(error.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        raise


def get_duration(media_path):
    """Duree du media en secondes."""
    return float(ffmpeg.probe(str(media_path))["format"]["duration"])


def extract_audio(media_path, audio_path):
    """Convertit la piste audio en wav mono 16 kHz, le format attendu par Whisper."""
    stream = ffmpeg.output(ffmpeg.input(str(media_path)), str(audio_path), ac=1, ar=16000)
    run_ffmpeg(stream)


def add_subtitle_track(video_path, subtitle_path, output_path, language):
    """Ajoute le .srt comme piste de sous-titres activable, sans re-encoder la video."""
    stream = ffmpeg.output(
        ffmpeg.input(str(video_path)),
        ffmpeg.input(str(subtitle_path)),
        str(output_path),
        **{
            "c": "copy",
            "c:s": "mov_text",
            # une seule piste de sous-titres : langue et titre vont sur la meme piste
            "metadata:s:s:0": f"language={language}",
            "metadata:s:s": f"title={Path(subtitle_path).stem}",
            # sans ce drapeau, la plupart des lecteurs n'affichent pas la piste
            # tant qu'on ne l'active pas a la main
            "disposition:s:0": "default",
        },
    )
    run_ffmpeg(stream)


def burn_subtitles(video_path, subtitle_path, output_path):
    """Dessine les sous-titres sur l'image (re-encodage de la video)."""
    # le filtre "subtitles" interprete le ":" de "C:" comme un separateur d'options
    filter_path = Path(subtitle_path).resolve().as_posix().replace(":", r"\:")
    stream = ffmpeg.output(ffmpeg.input(str(video_path)), str(output_path), vf=f"subtitles='{filter_path}'")
    run_ffmpeg(stream)
