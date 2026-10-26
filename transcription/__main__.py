"""Ligne de commande : python -m transcription <fichier> --format <format>"""

import argparse
import sys
import time
from pathlib import Path

from . import config
from .models import OutputFormat
from .pipeline import InvalidRequest, process, validate
from .transcribers import get_transcriber


def main():
    parser = argparse.ArgumentParser(prog="python -m transcription",
                                     description="Transcrit une video .mp4 ou un audio .wav.")
    parser.add_argument("input", help="fichier .mp4 ou .wav")
    parser.add_argument("-f", "--format", required=True, choices=[f.value for f in OutputFormat],
                        help="burned : video avec sous-titres dessines | "
                             "track : video avec piste de sous-titres + .srt | "
                             "subtitles : .srt + .vtt | text : .txt sans timestamp")
    parser.add_argument("-o", "--output-dir", default="output", help="dossier de sortie (defaut : output)")
    args = parser.parse_args()

    try:
        # on valide avant de charger le modele, qui prend plusieurs secondes
        validate(Path(args.input), OutputFormat(args.format))
        transcriber = get_transcriber(config.TRANSCRIBER, config.MODEL_NAME)
        start = time.perf_counter()
        result = process(args.input, args.format, args.output_dir, transcriber)
    except InvalidRequest as error:
        sys.exit(f"Erreur : {error}")

    for warning in result.warnings:
        print(f"Attention : {warning}")
    print(f"Traitement termine en {time.perf_counter() - start:.1f} s")
    for path in result.files:
        print(f"  {path}")


if __name__ == "__main__":
    main()
