"""Modeles de transcription.

Pour ajouter un modele : ecrire une sous-classe de Transcriber qui renvoie une
Transcription, puis l'enregistrer dans TRANSCRIBERS. Le reste du pipeline n'a pas
a changer. L'identification du locuteur se branche en remplissant Segment.speaker.
"""

from abc import ABC, abstractmethod

from .models import Segment, Transcription


class Transcriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path, duration) -> Transcription:
        """Transcrit un wav mono 16 kHz. `duration` sert a borner le dernier segment."""


def chunks_to_segments(chunks, duration):
    """Convertit les chunks du pipeline Hugging Face en segments propres."""
    segments = []
    for chunk in chunks:
        text = chunk["text"].strip()
        start, end = chunk["timestamp"]
        # le dernier chunk peut ne pas avoir de fin : on prend la fin du media
        if end is None:
            end = duration
        if not text or start is None or end <= start:
            continue
        segments.append(Segment(start=start, end=min(end, duration), text=text))
    return segments


class WhisperTranscriber(Transcriber):
    """Whisper via le pipeline Hugging Face. Le modele est charge une seule fois."""

    def __init__(self, model_name):
        # imports locaux : le reste du paquet (et ses tests) n'a pas besoin de torch
        import torch
        from transformers import pipeline

        # GPU si disponible, sinon CPU (le float16 n'est pas supporte sur CPU)
        if torch.cuda.is_available():
            device, dtype = "cuda:0", torch.float16
        else:
            device, dtype = "cpu", torch.float32
            print("Pas de GPU detecte : transcription sur CPU (plus lente).")
        self._pipeline = pipeline("automatic-speech-recognition", model_name,
                                  dtype=dtype, device=device)

    def transcribe(self, audio_path, duration):
        # Sans chunk_length_s, Whisper transcrit l'audio long sequentiellement, fenetre
        # par fenetre, en s'appuyant sur ses propres timestamps. Le mode "chunk" recolle
        # mal les morceaux et produisait des phrases en double aux jonctions.
        output = self._pipeline(str(audio_path), return_timestamps=True)
        segments = chunks_to_segments(output["chunks"], duration)
        return Transcription(text=output["text"].strip(), segments=segments)


TRANSCRIBERS = {"whisper": WhisperTranscriber}


def get_transcriber(name, model_name) -> Transcriber:
    if name not in TRANSCRIBERS:
        raise ValueError(f"Transcriber inconnu : {name} (disponibles : {', '.join(TRANSCRIBERS)})")
    return TRANSCRIBERS[name](model_name)
