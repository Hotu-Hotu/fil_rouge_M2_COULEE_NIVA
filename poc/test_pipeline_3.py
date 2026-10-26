# Dependances : pip install -r requirements.txt (a la racine du projet)
# Necessite ffmpeg installe sur la machine. Sous Windows : winget install ffmpeg, puis
# rouvrir le terminal (ou utiliser wsl).

import sys
import tempfile
from pathlib import Path

import ffmpeg
import torch
from transformers import pipeline

# paths are resolved from the script folder, so it works whatever the current directory
SCRIPT_DIR = Path(__file__).resolve().parent

INPUT_VIDEO = SCRIPT_DIR / "input.mp4"
OUTPUT_VIDEO = SCRIPT_DIR / "output.mp4"
MODEL_NAME = "openai/whisper-medium.en"
# True : sous-titres incrustes dans l'image (re-encodage de la video)
# False : piste de sous-titres separee, activable dans le lecteur (pas de re-encodage)
EMBEDDED_SUBTITLE = False


def run_ffmpeg(stream):
    """Lance ffmpeg sans polluer la console, et affiche son erreur s'il echoue."""
    try:
        ffmpeg.run(stream, overwrite_output=True, quiet=True)
    except ffmpeg.Error as error:
        print(error.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
        raise


def extract_audio(video_path, audio_path):
    """Extrait la piste audio en wav mono 16 kHz, le format attendu par Whisper."""
    stream = ffmpeg.output(ffmpeg.input(str(video_path)), str(audio_path), ac=1, ar=16000)
    run_ffmpeg(stream)


def get_duration(media_path):
    """Duree du media en secondes."""
    return float(ffmpeg.probe(str(media_path))["format"]["duration"])


def transcribe(audio_path):
    """Transcrit l'audio avec Whisper et renvoie le resultat avec les timestamps."""
    # GPU si disponible, sinon CPU (le float16 n'est pas supporte sur CPU)
    if torch.cuda.is_available():
        device, dtype = "cuda:0", torch.float16
    else:
        device, dtype = "cpu", torch.float32
        print("Pas de GPU detecte : transcription sur CPU (plus lente).")

    whisper = pipeline("automatic-speech-recognition", MODEL_NAME,
                       dtype=dtype, device=device)
    # Sans chunk_length_s, Whisper transcrit l'audio long sequentiellement, fenetre
    # par fenetre, en s'appuyant sur ses propres timestamps. Le mode "chunk" recolle
    # mal les morceaux et produisait des phrases en double aux jonctions.
    return whisper(str(audio_path), return_timestamps=True)


def format_time(seconds):
    """Formate un temps en secondes au format SRT : HH:MM:SS,mmm."""
    # on travaille en millisecondes entieres pour eviter les arrondis du type 59,9996 -> 59,1000
    total_ms = round(seconds * 1000)
    hours, total_ms = divmod(total_ms, 3_600_000)
    minutes, total_ms = divmod(total_ms, 60_000)
    secs, milliseconds = divmod(total_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def build_srt(chunks, duration):
    """Construit le contenu d'un fichier SRT a partir des chunks de Whisper."""
    blocks = []
    for chunk in chunks:
        text = chunk["text"].strip()
        start, end = chunk["timestamp"]
        # le dernier chunk peut ne pas avoir de fin : on prend la fin de la video
        if end is None:
            end = duration
        if not text or start is None or end <= start:
            continue
        # numerotation continue, meme si des chunks sont ignores
        number = len(blocks) + 1
        blocks.append(f"{number}\n{format_time(start)} --> {format_time(end)}\n{text}\n")
    return "\n".join(blocks)


def add_subtitles(video_path, subtitle_path, output_path, embedded):
    """Ajoute les sous-titres a la video, en piste separee ou incrustes dans l'image."""
    video = ffmpeg.input(str(video_path))
    track_title = subtitle_path.name.replace(".srt", "")
    if not embedded:
        subtitles = ffmpeg.input(str(subtitle_path))
        stream = ffmpeg.output(
            video, subtitles, str(output_path),
            **{"c": "copy", "c:s": "mov_text",
               # une seule piste de sous-titres : langue et titre vont sur la meme piste
               "metadata:s:s:0": "language=eng",
               "metadata:s:s": f"title={track_title}",
               # sans ce drapeau, la plupart des lecteurs n'affichent pas la piste
               # tant qu'on ne l'active pas a la main
               "disposition:s:0": "default"}
        )
    else:
        # le filtre "subtitles" interprete le ":" de "C:" comme un separateur d'options
        filter_path = subtitle_path.as_posix().replace(":", r"\:")
        stream = ffmpeg.output(video, str(output_path), vf=f"subtitles='{filter_path}'")
    run_ffmpeg(stream)


def main():
    if not INPUT_VIDEO.exists():
        sys.exit(f"Video introuvable : {INPUT_VIDEO}")

    video_name = INPUT_VIDEO.stem
    subtitle_file = SCRIPT_DIR / f"sub-{video_name}.en.srt"

    # l'audio extrait est un fichier intermediaire : on le met dans un dossier temporaire
    with tempfile.TemporaryDirectory() as tmp_dir:
        extracted_audio = Path(tmp_dir) / f"audio-{video_name}.wav"
        extract_audio(INPUT_VIDEO, extracted_audio)
        transcription = transcribe(extracted_audio)

    srt_content = build_srt(transcription["chunks"], get_duration(INPUT_VIDEO))
    subtitle_file.write_text(srt_content, encoding="utf-8")

    add_subtitles(INPUT_VIDEO, subtitle_file, OUTPUT_VIDEO, EMBEDDED_SUBTITLE)

    print(transcription["text"])
    print(f"\nSous-titres : {subtitle_file}\nVideo : {OUTPUT_VIDEO}")


if __name__ == "__main__":
    main()
