# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Soroush Yousefpour

"""Text-to-audio generation pipeline for Kokoro TTS."""

from __future__ import annotations

import re

import numpy as np

from .config import KokoroConfig
from .model import KokoroModel
from .phonemize import Phonemizer
from .voices import VoiceManager

SAMPLE_RATE = 24000
_INTER_CHUNK_PAUSE_SECONDS = 0.05
_SINGLE_NEWLINE_PAUSE_SECONDS = 0.16
_MULTILINE_BREAK_PAUSE_SECONDS = 0.28


def _resample_2x(audio: np.ndarray) -> np.ndarray:
    """Upsample audio by exactly 2x using FFT zero-padding.

    For a real signal of length N, the rfft has N//2+1 bins.  Padding the
    spectrum to 2x length and taking the irfft produces a perfectly
    bandlimited 2x-upsampled signal.  Numpy-only, no extra dependencies.
    """
    n = len(audio)
    spectrum = np.fft.rfft(audio)
    out_len = n * 2
    padded = np.zeros(out_len // 2 + 1, dtype=spectrum.dtype)
    padded[: len(spectrum)] = spectrum
    return np.fft.irfft(padded, n=out_len).astype(np.float32) * 2.0


def _silence(duration_seconds: float, sample_rate: int) -> np.ndarray:
    sample_count = int(round(duration_seconds * sample_rate))
    if sample_count <= 0:
        return np.array([], dtype=np.float32)
    return np.zeros(sample_count, dtype=np.float32)


def _prepare_audio_chunk(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    chunk = np.array(audio.tolist(), dtype=np.float32)
    if sample_rate == 48000 and len(chunk) > 0:
        chunk = _resample_2x(chunk)
    return chunk


def _split_text_blocks(text: str) -> list[tuple[str, float]]:
    """Split text on line breaks and annotate the pause after each block."""
    parts = re.split(r"(\n+)", text)
    blocks: list[tuple[str, float]] = []

    for index in range(0, len(parts), 2):
        block = parts[index].strip()
        if not block:
            continue

        pause = 0.0
        if index + 1 < len(parts):
            newline_count = len(parts[index + 1])
            pause = _MULTILINE_BREAK_PAUSE_SECONDS if newline_count >= 2 else _SINGLE_NEWLINE_PAUSE_SECONDS

        blocks.append((block, pause))

    return blocks


def _iter_audio_chunks(
    text: str,
    model: KokoroModel,
    config: KokoroConfig,
    voice_manager: VoiceManager,
    voice: str,
    speed: float,
    phonemizer: Phonemizer | None,
    sample_rate: int,
):
    if phonemizer is None:
        phonemizer = Phonemizer(config.vocab)

    blocks = _split_text_blocks(text)
    if not blocks:
        return

    voice_array = voice_manager.load_voice(voice)

    for block_text, block_pause in blocks:
        chunks = phonemizer.phonemize_long(block_text)
        if not chunks:
            continue

        for index, (phonemes, token_ids) in enumerate(chunks):
            style = voice_manager.get_style(voice_array, len(token_ids))
            audio = model.forward(phonemes, style, speed)
            yield _prepare_audio_chunk(audio, sample_rate)

            if index < len(chunks) - 1:
                yield _silence(_INTER_CHUNK_PAUSE_SECONDS, sample_rate)

        if block_pause > 0:
            yield _silence(block_pause, sample_rate)


def generate(
    text: str,
    model: KokoroModel,
    config: KokoroConfig,
    voice_manager: VoiceManager,
    voice: str = "af_heart",
    speed: float = 1.0,
    phonemizer: Phonemizer | None = None,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """Full text-to-audio pipeline.

    Args:
        text: Input text to synthesize.
        model: Loaded KokoroModel.
        config: KokoroConfig instance.
        voice_manager: VoiceManager instance.
        voice: Voice name to use for synthesis.
        speed: Speaking rate multiplier (>1 is faster, <1 is slower).
        phonemizer: Optional pre-built Phonemizer to avoid re-initializing.
        sample_rate: Output sample rate. 24000 (native) or 48000 (2x upsampled).

    Returns:
        Float32 numpy array of audio samples at the requested sample rate.
    """
    audio_chunks = list(
        _iter_audio_chunks(
            text=text,
            model=model,
            config=config,
            voice_manager=voice_manager,
            voice=voice,
            speed=speed,
            phonemizer=phonemizer,
            sample_rate=sample_rate,
        )
    )
    if not audio_chunks:
        return np.array([], dtype=np.float32)

    return np.concatenate(audio_chunks)


def generate_stream(
    text: str,
    model: KokoroModel,
    config: KokoroConfig,
    voice_manager: VoiceManager,
    voice: str = "af_heart",
    speed: float = 1.0,
    phonemizer: Phonemizer | None = None,
    sample_rate: int = SAMPLE_RATE,
):
    """Generate audio in chunks as they are produced.

    Yields float32 numpy arrays, one per phoneme chunk. Suitable for
    low-latency streaming playback.

    Args:
        text: Input text to synthesize.
        model: Loaded KokoroModel.
        config: KokoroConfig instance.
        voice_manager: VoiceManager instance.
        voice: Voice name to use for synthesis.
        speed: Speaking rate multiplier.
        phonemizer: Optional pre-built Phonemizer to avoid re-initializing.
        sample_rate: Output sample rate. 24000 (native) or 48000 (2x upsampled).

    Yields:
        Float32 numpy arrays, one per sentence chunk.
    """
    yield from _iter_audio_chunks(
        text=text,
        model=model,
        config=config,
        voice_manager=voice_manager,
        voice=voice,
        speed=speed,
        phonemizer=phonemizer,
        sample_rate=sample_rate,
    )
