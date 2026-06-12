"""Tests for complete offline macOS packaging helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

PREPARE_MODEL = Path(__file__).parents[1] / "packaging/prepare_model.py"
SPEC = importlib.util.spec_from_file_location("kokoro_prepare_model", PREPARE_MODEL)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
copy_model = MODULE.copy_model


def test_prepare_model_keeps_only_runtime_resources(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    voices = source / "voices"
    samples = source / "samples"
    voices.mkdir(parents=True)
    samples.mkdir()

    (source / "config.json").write_text("{}", encoding="utf-8")
    (source / "kokoro-v1_0.safetensors").write_bytes(b"weights")
    (source / "README.md").write_text("model", encoding="utf-8")
    (samples / "sample.wav").write_bytes(b"sample")
    for index in range(54):
        (voices / f"voice-{index}.safetensors").write_bytes(b"voice")
        (voices / f"voice-{index}.pt").write_bytes(b"duplicate")

    copy_model(source, destination)

    assert len(list((destination / "voices").glob("*.safetensors"))) == 54
    assert not list(destination.rglob("*.pt"))
    assert not (destination / "samples").exists()
