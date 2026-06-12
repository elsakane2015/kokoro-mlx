"""Tests for the optional local HTTP interface."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import numpy as np
import pytest

# Optional dependency checks intentionally precede the imports below.
# ruff: noqa: E402

fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from kokoro_mlx import TTSResult
from kokoro_mlx.web.app import create_app
from kokoro_mlx.web.backend import prepare_frozen_environment
from kokoro_mlx.web.cli import DEFAULT_PORT, bundled_model_path, resolve_model, resolve_port, valid_port
from kokoro_mlx.web.schemas import SpeechRequest
from kokoro_mlx.web.service import ServiceBusyError, SynthesisService


class FakeTTS:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def list_voices(self) -> list[str]:
        return ["af_heart", "zf_xiaobei"]

    def generate(
        self,
        text: str,
        voice: str,
        speed: float,
        sample_rate: int,
        language: str | None,
    ) -> TTSResult:
        self.calls.append(
            {
                "text": text,
                "voice": voice,
                "speed": speed,
                "sample_rate": sample_rate,
                "language": language,
            }
        )
        audio = np.zeros(sample_rate // 10, dtype=np.float32)
        return TTSResult(audio=audio, sample_rate=sample_rate, duration=0.1, voice=voice)


def test_local_pages_and_health() -> None:
    app = create_app(tts=FakeTTS())
    with TestClient(app) as client:
        index = client.get("/")
        favicon = client.get("/favicon.ico")
        health = client.get("/api/health")
        voices = client.get("/api/voices")

    assert index.status_code == 200
    assert "kokoro-mlx" in index.text
    assert favicon.status_code == 204
    assert health.json()["model_loaded"] is True
    assert health.json()["voice_count"] == 2
    assert voices.json()["default_voice"] == "zf_xiaobei"
    assert voices.json()["voices"] == ["af_heart", "zf_xiaobei"]


def test_speech_endpoint_returns_wav() -> None:
    fake_tts = FakeTTS()
    app = create_app(tts=fake_tts)

    with TestClient(app) as client:
        response = client.post(
            "/api/speech",
            json={
                "text": "你好",
                "voice": "zf_xiaobei",
                "language": "zh",
                "speed": 1.25,
                "sample_rate": 48000,
            },
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["x-audio-duration"] == "0.100"
    assert response.headers["x-audio-sample-rate"] == "48000"
    assert response.content.startswith(b"RIFF")
    assert fake_tts.calls[0]["language"] == "zh"


def test_download_endpoint_returns_latest_wav() -> None:
    fake_tts = FakeTTS()
    app = create_app(tts=fake_tts)

    with TestClient(app) as client:
        initial = client.get("/api/speech/download")
        synth = client.post(
            "/api/speech",
            json={
                "text": "你好",
                "voice": "zf_xiaobei",
                "sample_rate": 24000,
            },
        )
        download = client.get("/api/speech/download")

    assert initial.status_code == 404
    assert synth.status_code == 200
    assert download.status_code == 200
    assert download.headers["content-disposition"] == 'attachment; filename="speech.wav"'
    assert download.content.startswith(b"RIFF")


def test_speech_endpoint_maps_overlong_runtime_error_to_400() -> None:
    class OverlongTTS(FakeTTS):
        def generate(self, *args, **kwargs):
            raise RuntimeError("[metal::malloc] Attempting to allocate 13902151680 bytes which is greater than the maximum allowed buffer size of 8589934592 bytes.")

    app = create_app(tts=OverlongTTS())

    with TestClient(app) as client:
        response = client.post(
            "/api/speech",
            json={
                "text": "你好",
                "voice": "zf_xiaobei",
            },
        )

    assert response.status_code == 400
    assert "expanded beyond the model limit" in response.json()["detail"]


@pytest.mark.parametrize(
    ("payload", "status_code"),
    [
        ({"text": "   "}, 422),
        ({"text": "hello", "speed": 0}, 422),
        ({"text": "hello", "sample_rate": 44100}, 422),
        ({"text": "hello", "voice": "missing"}, 400),
    ],
)
def test_speech_endpoint_rejects_invalid_requests(payload: dict[str, object], status_code: int) -> None:
    app = create_app(tts=FakeTTS())
    with TestClient(app) as client:
        response = client.post("/api/speech", json=payload)
    assert response.status_code == status_code


def test_service_rejects_concurrent_inference() -> None:
    started = threading.Event()
    release = threading.Event()

    class BlockingTTS(FakeTTS):
        def generate(self, *args, **kwargs) -> TTSResult:
            started.set()
            release.wait(timeout=2)
            return super().generate(*args, **kwargs)

    service = SynthesisService(BlockingTTS())
    request = SpeechRequest(text="hello")
    worker = threading.Thread(target=service.synthesize, args=(request,))
    worker.start()
    assert started.wait(timeout=1)

    with pytest.raises(ServiceBusyError):
        service.synthesize(request)

    release.set()
    worker.join(timeout=2)
    assert not worker.is_alive()


def test_port_resolution_precedence() -> None:
    assert resolve_port(9000, {"KOKORO_MLX_PORT": "9100"}) == 9000
    assert resolve_port(None, {"KOKORO_MLX_PORT": "9100"}) == 9100
    assert resolve_port(None, {}) == DEFAULT_PORT


def test_model_resolution_precedence() -> None:
    assert resolve_model("/cli/model", {"KOKORO_MLX_MODEL": "/env/model"}) == "/cli/model"
    assert resolve_model(None, {"KOKORO_MLX_MODEL": "/env/model"}) == "/env/model"


def test_bundled_model_resolution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model = tmp_path / "model"
    model.mkdir()
    monkeypatch.setattr("kokoro_mlx.web.cli.sys._MEIPASS", str(tmp_path), raising=False)
    assert bundled_model_path() == model
    assert resolve_model(None, {}) == str(model)


def test_frozen_environment_forces_offline_resources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dictionary = tmp_path / "pyopenjtalk/open_jtalk_dic_utf_8-1.11"
    dictionary.mkdir(parents=True)
    monkeypatch.setattr("kokoro_mlx.web.backend.sys._MEIPASS", str(tmp_path), raising=False)
    prepare_frozen_environment()
    assert Path(os.environ["OPEN_JTALK_DICT_DIR"]) == dictionary
    assert os.environ["HF_HUB_OFFLINE"] == "1"


@pytest.mark.parametrize("value", ["0", "65536", "not-a-port"])
def test_port_validation_rejects_invalid_values(value: str) -> None:
    with pytest.raises(Exception):
        valid_port(value)
