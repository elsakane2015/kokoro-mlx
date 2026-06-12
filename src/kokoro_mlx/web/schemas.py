"""Request schemas for the local HTTP API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from kokoro_mlx.voices import DEFAULT_VOICE


class SpeechRequest(BaseModel):
    """Validated text-to-speech request."""

    text: str = Field(min_length=1, max_length=5000)
    voice: str = Field(default=DEFAULT_VOICE, min_length=1, max_length=100)
    language: str | None = Field(default=None, max_length=32)
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    sample_rate: Literal[24000, 48000] = 24000

    @field_validator("text")
    @classmethod
    def text_must_contain_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text must contain at least one non-whitespace character.")
        return value

    @field_validator("voice")
    @classmethod
    def normalize_voice(cls, value: str) -> str:
        return value.strip()

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None
