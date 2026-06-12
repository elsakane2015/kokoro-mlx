"""FastAPI application for local kokoro-mlx usage."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from kokoro_mlx import DEFAULT_VOICE, KokoroTTS, __version__

from .schemas import SpeechRequest
from .service import LanguageSetupError, ServiceBusyError, SynthesisService, UnknownVoiceError

DEFAULT_MODEL = "mlx-community/Kokoro-82M-bf16"
LOCAL_DEFAULT_VOICE = "zf_xiaobei"
STATIC_DIR = Path(__file__).with_name("static")


def _service(request: Request) -> SynthesisService:
    return request.app.state.synthesis_service


def create_app(
    tts: KokoroTTS | None = None,
    model_id_or_path: str = DEFAULT_MODEL,
) -> FastAPI:
    """Create the local-only HTTP application.

    Passing a pre-built ``tts`` instance is primarily useful for tests and
    embedding. Otherwise the model is loaded once during application startup.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        instance = tts or KokoroTTS.from_pretrained(model_id_or_path)
        app.state.synthesis_service = SynthesisService(instance)
        try:
            yield
        finally:
            if tts is None:
                instance.close()

    app = FastAPI(
        title="kokoro-mlx local server",
        description="Local-only text-to-speech API powered by kokoro-mlx.",
        version=__version__,
        lifespan=lifespan,
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/favicon.ico", include_in_schema=False, status_code=204)
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/api/health")
    def health(request: Request) -> dict[str, object]:
        voices = _service(request).list_voices()
        return {
            "status": "ok",
            "model_loaded": True,
            "voice_count": len(voices),
            "version": __version__,
        }

    @app.get("/api/voices")
    def voices(request: Request) -> dict[str, object]:
        available_voices = _service(request).list_voices()
        default_voice = LOCAL_DEFAULT_VOICE if LOCAL_DEFAULT_VOICE in available_voices else DEFAULT_VOICE
        return {
            "default_voice": default_voice,
            "voices": available_voices,
        }

    @app.post("/api/speech", response_class=Response)
    def speech(payload: SpeechRequest, request: Request) -> Response:
        try:
            audio = _service(request).synthesize(payload)
        except ServiceBusyError as exc:
            raise HTTPException(
                status_code=503,
                detail=str(exc),
                headers={"Retry-After": "1"},
            ) from exc
        except LanguageSetupError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except (UnknownVoiceError, FileNotFoundError, ImportError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return Response(
            content=audio.wav,
            media_type="audio/wav",
            headers={
                "Content-Disposition": 'attachment; filename="speech.wav"',
                "X-Audio-Duration": f"{audio.duration:.3f}",
                "X-Audio-Sample-Rate": str(audio.sample_rate),
                "X-Audio-Voice": audio.voice,
            },
        )

    @app.get("/api/speech/download", response_class=Response)
    def download_latest(request: Request) -> Response:
        audio = _service(request).latest_audio()
        if audio is None:
            raise HTTPException(status_code=404, detail="No synthesized audio is available yet.")
        return Response(
            content=audio.wav,
            media_type="audio/wav",
            headers={
                "Content-Disposition": 'attachment; filename="speech.wav"',
                "X-Audio-Duration": f"{audio.duration:.3f}",
                "X-Audio-Sample-Rate": str(audio.sample_rate),
                "X-Audio-Voice": audio.voice,
            },
        )

    return app
