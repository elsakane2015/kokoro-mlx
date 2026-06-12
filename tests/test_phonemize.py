"""Tests for phonemization chunking."""

from __future__ import annotations

from kokoro_mlx.phonemize import Phonemizer


def _make_stub_phonemizer() -> Phonemizer:
    phonemizer = Phonemizer.__new__(Phonemizer)
    phonemizer._vocab = {char: index + 1 for index, char in enumerate("abcdefghijklmnopqrstuvwxyz ")}
    phonemizer._language = "en-us"
    phonemizer._g2p = object()
    phonemizer._phonemes_for_text = lambda text: text  # type: ignore[method-assign]
    return phonemizer


def test_phonemize_long_splits_single_overlong_sentence() -> None:
    phonemizer = _make_stub_phonemizer()
    text = "a" * 1200

    chunks = phonemizer.phonemize_long(text)

    assert len(chunks) > 1
    assert all(len(token_ids) <= 512 for _, token_ids in chunks)
    assert "".join(phonemes for phonemes, _ in chunks) == text


def test_phonemize_long_splits_overlong_phoneme_output() -> None:
    phonemizer = _make_stub_phonemizer()
    phonemizer._token_count = lambda text: 1  # type: ignore[method-assign]
    phonemizer._phonemes_for_text = lambda text: text  # type: ignore[method-assign]
    text = "a" * 1200

    chunks = phonemizer.phonemize_long(text)

    assert len(chunks) > 1
    assert all(len(token_ids) <= 512 for _, token_ids in chunks)
    assert "".join(phonemes for phonemes, _ in chunks) == text
