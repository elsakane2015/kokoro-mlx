"""Frozen backend entry point used by the native macOS application."""

import os
import sys
from multiprocessing import freeze_support
from pathlib import Path

from kokoro_mlx.web.cli import main


def prepare_frozen_environment() -> None:
    """Force the packaged application to use only bundled offline resources."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if not bundle_root:
        return

    root = Path(bundle_root)
    open_jtalk_dictionary = root / "pyopenjtalk/open_jtalk_dic_utf_8-1.11"
    if not open_jtalk_dictionary.is_dir():
        raise RuntimeError("The bundled Japanese dictionary is missing.")

    os.environ.update(
        {
            "HF_HUB_OFFLINE": "1",
            "OPEN_JTALK_DICT_DIR": str(open_jtalk_dictionary),
            "TRANSFORMERS_OFFLINE": "1",
        }
    )


if __name__ == "__main__":
    freeze_support()
    prepare_frozen_environment()
    main()
