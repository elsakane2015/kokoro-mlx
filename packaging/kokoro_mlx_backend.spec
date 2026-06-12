# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs, copy_metadata

ROOT = Path(SPEC).resolve().parents[1]

datas = []
binaries = []
hiddenimports = []

for package in ("en_core_web_sm", "espeakng_loader", "pyopenjtalk"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

for package in ("language_tags", "misaki", "mlx"):
    datas += collect_data_files(package)

binaries += collect_dynamic_libs("mlx")

for distribution in ("fastapi", "kokoro-mlx", "misaki", "mlx", "pydantic", "spacy", "starlette", "uvicorn"):
    datas += copy_metadata(distribution)

datas += [(str(ROOT / "src/kokoro_mlx/web/static"), "kokoro_mlx/web/static")]

a = Analysis(
    [str(ROOT / "src/kokoro_mlx/web/backend.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports
    + [
        "kokoro_mlx.web.backend",
        "en_core_web_sm",
        "misaki.en",
        "misaki.espeak",
        "misaki.ja",
        "misaki.zh",
        "mlx._reprlib_fix",
        "mlx.core",
        "mlx.nn",
        "pyopenjtalk",
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "build",
        "fsspec",
        "hatchling",
        "hf_xet",
        "huggingface_hub",
        "misaki.he",
        "misaki.ko",
        "misaki.vi",
        "misaki.vi_cleaner",
        "misaki.zh_frontend",
        "pypinyin_dict",
        "pytest",
        "ruff",
        "sounddevice",
        "spacy.tests",
        "thinc.tests",
        "torch",
        "torchgen",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="kokoro-mlx-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    target_arch="arm64",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="kokoro-mlx-backend",
)
