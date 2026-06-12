# Third-Party Notices

Kokoro MLX includes open-source software and model assets. The files below
summarize the primary projects included in the macOS distribution. Original
license and NOTICE files collected from the build environment are included in
the DMG under `Third-Party Licenses`.

## Kokoro MLX

- Project: `gabrimatic/kokoro-mlx`
- License: MIT
- Source: <https://github.com/gabrimatic/kokoro-mlx>
- Full license: `LICENSE`

## Kokoro Model and Voices

- Model: `mlx-community/Kokoro-82M-bf16`
- Original model: `hexagrad/Kokoro-82M`
- License declared by the model card: Apache License 2.0
- Source: <https://huggingface.co/mlx-community/Kokoro-82M-bf16>

The bundled model directory includes its upstream `README.md` and `VOICES.md`.
The model card is also included in the DMG as
`Third-Party Licenses/Kokoro-Model-README.md`.

## Primary Runtime Components

- MLX: <https://github.com/ml-explore/mlx>
- FastAPI: <https://github.com/fastapi/fastapi>
- Uvicorn: <https://github.com/encode/uvicorn>
- NumPy: <https://github.com/numpy/numpy>
- SoundFile/libsndfile: <https://github.com/bastibe/python-soundfile>
- safetensors: <https://github.com/huggingface/safetensors>
- Misaki: <https://github.com/hexgrad/misaki>
- eSpeak NG: <https://github.com/espeak-ng/espeak-ng>
- spaCy and `en_core_web_sm`: <https://github.com/explosion/spaCy>
- pyopenjtalk: <https://github.com/r9y9/pyopenjtalk>

Review the corresponding upstream repositories for their complete license
texts and attribution requirements before redistributing modified builds.
