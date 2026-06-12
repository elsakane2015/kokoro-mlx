"""Thread-safe service layer for the local HTTP API."""

from __future__ import annotations

import io
import threading
from dataclasses import dataclass

import soundfile as sf

from kokoro_mlx import KokoroTTS

from .schemas import SpeechRequest


class ServiceBusyError(RuntimeError):
    """Raised when another synthesis request is already running."""


class UnknownVoiceError(ValueError):
    """Raised when a request references an unavailable voice."""


class LanguageSetupError(RuntimeError):
    """Raised when a language dependency cannot be initialized."""


@dataclass(frozen=True)
class SpeechAudio:
    """Encoded WAV response and metadata."""

    wav: bytes
    duration: float
    sample_rate: int
    voice: str


class SynthesisService:
    """Owns one model instance and permits one active inference at a time."""

    def __init__(self, tts: KokoroTTS) -> None:
        self._tts = tts
        self._inference_slot = threading.BoundedSemaphore(value=1)
        self._latest_audio_lock = threading.Lock()
        self._latest_audio: SpeechAudio | None = None

    def list_voices(self) -> list[str]:
        return self._tts.list_voices()

    def latest_audio(self) -> SpeechAudio | None:
        with self._latest_audio_lock:
            return self._latest_audio

    def synthesize(self, request: SpeechRequest) -> SpeechAudio:
        if request.voice not in self.list_voices():
            raise UnknownVoiceError(f"Unknown voice: {request.voice}")

        if not self._inference_slot.acquire(blocking=False):
            raise ServiceBusyError("Another synthesis request is currently running.")

        try:
            try:
                result = self._tts.generate(
                    request.text,
                    voice=request.voice,
                    speed=request.speed,
                    sample_rate=request.sample_rate,
                    language=request.language,
                )
            except SystemExit as exc:
                raise LanguageSetupError(
                    "The selected language resources could not be initialized. "
                    "Install the matching kokoro-mlx language extra and try again."
                ) from exc
            except RuntimeError as exc:
                message = str(exc)
                if "Attempting to allocate" in message and "maximum allowed buffer size" in message:
                    raise ValueError(
                        "The input text expanded beyond the model limit after chunking. "
                        "Please shorten the text or report this as a bug."
                    ) from exc
                raise
            output = io.BytesIO()
            sf.write(output, result.audio, result.sample_rate, format="WAV", subtype="PCM_16")
            audio = SpeechAudio(
                wav=output.getvalue(),
                duration=result.duration,
                sample_rate=result.sample_rate,
                voice=result.voice,
            )
            with self._latest_audio_lock:
                self._latest_audio = audio
            return audio
        finally:
            self._inference_slot.release()
