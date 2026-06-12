"""Prepare a minimal complete offline Kokoro model directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

MODEL_ID = "mlx-community/Kokoro-82M-bf16"
ROOT_FILES = ("config.json", "kokoro-v1_0.safetensors", "README.md", "VOICES.md")


def copy_model(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for name in ROOT_FILES:
        source_file = source / name
        if source_file.exists():
            shutil.copy2(source_file, destination / name, follow_symlinks=True)

    voices = destination / "voices"
    voices.mkdir()
    for source_file in sorted((source / "voices").glob("*.safetensors")):
        shutil.copy2(source_file, voices / source_file.name, follow_symlinks=True)

    if not (destination / "config.json").is_file():
        raise RuntimeError("prepared model is missing config.json")
    if not (destination / "kokoro-v1_0.safetensors").is_file():
        raise RuntimeError("prepared model is missing model weights")
    if len(list(voices.glob("*.safetensors"))) != 54:
        raise RuntimeError("prepared model must contain exactly 54 safetensors voices")


def download_model() -> Path:
    from huggingface_hub import snapshot_download

    return Path(
        snapshot_download(
            repo_id=MODEL_ID,
            allow_patterns=[
                "config.json",
                "kokoro-v1_0.safetensors",
                "README.md",
                "VOICES.md",
                "voices/*.safetensors",
            ],
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    copy_model(args.source or download_model(), args.destination)


if __name__ == "__main__":
    main()
