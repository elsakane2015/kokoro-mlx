"""Command-line entry point for the local HTTP server."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

DEFAULT_PORT = 8000
PORT_ENV = "KOKORO_MLX_PORT"
MODEL_ENV = "KOKORO_MLX_MODEL"
APP_MODEL_RELATIVE_PATH = Path("model")


def valid_port(value: str | int) -> int:
    """Parse and validate a TCP port."""
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def resolve_port(cli_port: int | None, environ: dict[str, str] | None = None) -> int:
    """Resolve port using CLI, environment, then default precedence."""
    if cli_port is not None:
        return valid_port(cli_port)
    env = os.environ if environ is None else environ
    value = env.get(PORT_ENV)
    return valid_port(value) if value else DEFAULT_PORT


def bundled_model_path() -> Path | None:
    """Return the bundled model directory when running from a frozen app."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if not bundle_root:
        return None
    path = Path(bundle_root) / APP_MODEL_RELATIVE_PATH
    return path if path.is_dir() else None


def resolve_model(cli_model: str | None, environ: dict[str, str] | None = None) -> str:
    """Resolve model using CLI, environment, bundled resource, then Hub ID."""
    if cli_model:
        return cli_model
    env = os.environ if environ is None else environ
    if value := env.get(MODEL_ENV):
        return value
    if path := bundled_model_path():
        return str(path)
    return "mlx-community/Kokoro-82M-bf16"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the kokoro-mlx local web interface.")
    parser.add_argument(
        "--port",
        type=valid_port,
        help=f"Local HTTP port. Overrides {PORT_ENV}; default: {DEFAULT_PORT}.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=f"Local model directory or Hugging Face repo ID. Can also use {MODEL_ENV}.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        port = resolve_port(args.port)
    except argparse.ArgumentTypeError as exc:
        parser.error(f"{PORT_ENV}: {exc}")

    import uvicorn

    from .app import create_app

    print(f"kokoro-mlx local server: http://127.0.0.1:{port}")
    uvicorn.run(
        create_app(model_id_or_path=resolve_model(args.model)),
        host="127.0.0.1",
        port=port,
        workers=1,
    )


if __name__ == "__main__":
    main()
