# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Soroush Yousefpour

"""G2P phonemization pipeline using misaki."""

from __future__ import annotations

import re

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_MAX_TOKENS = 510  # context window is 512; 2 slots reserved for pad tokens

VOICE_PREFIX_LANGUAGES: dict[str, str] = {
    "af": "en-us",
    "am": "en-us",
    "bf": "en-gb",
    "bm": "en-gb",
    "ef": "es",
    "em": "es",
    "ff": "fr-fr",
    "hf": "hi",
    "hm": "hi",
    "if": "it",
    "im": "it",
    "jf": "ja",
    "jm": "ja",
    "pf": "pt-br",
    "pm": "pt-br",
    "zf": "zh",
    "zm": "zh",
}

LANGUAGE_ALIASES: dict[str, str] = {
    "a": "en-us",
    "en": "en-us",
    "en-us": "en-us",
    "english": "en-us",
    "american english": "en-us",
    "b": "en-gb",
    "en-gb": "en-gb",
    "british english": "en-gb",
    "e": "es",
    "es": "es",
    "spanish": "es",
    "f": "fr-fr",
    "fr": "fr-fr",
    "fr-fr": "fr-fr",
    "french": "fr-fr",
    "h": "hi",
    "hi": "hi",
    "hindi": "hi",
    "i": "it",
    "it": "it",
    "italian": "it",
    "j": "ja",
    "ja": "ja",
    "japanese": "ja",
    "p": "pt-br",
    "pt": "pt-br",
    "pt-br": "pt-br",
    "portuguese": "pt-br",
    "z": "zh",
    "zh": "zh",
    "chinese": "zh",
    "mandarin": "zh",
    "mandarin chinese": "zh",
}


def normalize_language(language: str | None) -> str:
    """Return the normalized Kokoro/misaki language code."""
    if language is None:
        return "en-us"
    key = language.strip().lower()
    return LANGUAGE_ALIASES.get(key, key)


def language_from_voice(voice: str) -> str:
    """Infer a normalized language code from a Kokoro voice name."""
    first_voice = voice.split(",", 1)[0].strip()
    return VOICE_PREFIX_LANGUAGES.get(first_voice[:2].lower(), "en-us")


class Phonemizer:
    """Grapheme-to-phoneme pipeline wrapping misaki's English G2P."""

    def __init__(self, vocab: dict[str, int], language: str = "en") -> None:
        self._vocab = vocab
        self._language = normalize_language(language)
        self._g2p = self._build_g2p(language)

    @staticmethod
    def _build_g2p(language: str):
        language = normalize_language(language)
        if language in ("en-us", "en-gb"):
            from misaki import en

            fallback = None
            try:
                from misaki import espeak

                fallback = espeak.EspeakFallback(british=language == "en-gb")
            except Exception:
                fallback = None

            # unk="" suppresses the '❓' sentinel that misaki emits for
            # unresolvable tokens (e.g. colons in time expressions).  Without
            # this, the sentinel passes through to _ids_from_phonemes where it
            # is silently dropped because '❓' is not in Kokoro's vocab,
            # potentially merging surrounding phonemes and distorting output.
            return en.G2P(unk="", british=language == "en-gb", fallback=fallback)
        if language == "ja":
            from misaki import ja

            # pyopenjtalk ships its dictionary and remains fully offline.
            return ja.JAG2P(version="pyopenjtalk")
        if language == "zh":
            from misaki import zh

            return zh.ZHG2P()

        from misaki import espeak

        return espeak.EspeakG2P(language=language)

    def _phonemes_for_text(self, text: str) -> str:
        result = self._g2p(text)
        if isinstance(result, tuple):
            return str(result[0] or "")
        return str(result or "")

    def _ids_from_phonemes(self, phonemes: str) -> list[int]:
        ids = [self._vocab[c] for c in phonemes if c in self._vocab]
        return [0, *ids, 0]

    def _token_count(self, text: str) -> int:
        """Count model tokens produced by *text* after phonemization."""
        phonemes = self._phonemes_for_text(text)
        return self._token_count_from_phonemes(phonemes)

    def _token_count_from_phonemes(self, phonemes: str) -> int:
        """Count model tokens already present in a phoneme string."""
        return len(self._ids_from_phonemes(phonemes)) - 2

    def _split_text_to_limit(self, text: str, max_tokens: int) -> list[str]:
        """Split *text* so each chunk stays within the model context window."""
        text = text.strip()
        if not text:
            return []

        if self._token_count(text) <= max_tokens:
            return [text]

        words = re.findall(r"\S+\s*", text)
        if len(words) <= 1:
            chunks: list[str] = []
            current = ""
            for char in text:
                candidate = current + char
                if current and self._token_count(candidate) > max_tokens:
                    if current.strip():
                        chunks.append(current.strip())
                    current = char
                else:
                    current = candidate
            if current.strip():
                chunks.append(current.strip())
            return chunks

        chunks: list[str] = []
        current = ""
        for word in words:
            candidate = current + word
            if current and self._token_count(candidate) > max_tokens:
                chunks.extend(self._split_text_to_limit(current, max_tokens))
                current = word
            else:
                current = candidate

        if current.strip():
            chunks.extend(self._split_text_to_limit(current, max_tokens) if self._token_count(current) > max_tokens else [current.strip()])

        return chunks

    def _split_phonemes_to_limit(self, phonemes: str, max_tokens: int) -> list[str]:
        """Split a phoneme string so each chunk stays within the model context window."""
        phonemes = phonemes.strip()
        if not phonemes:
            return []

        if self._token_count_from_phonemes(phonemes) <= max_tokens:
            return [phonemes]

        chunks: list[str] = []
        current = ""
        for char in phonemes:
            candidate = current + char
            if current and self._token_count_from_phonemes(candidate) > max_tokens:
                if current.strip():
                    chunks.append(current.strip())
                current = char
            else:
                current = candidate

        if current.strip():
            chunks.append(current.strip())

        return chunks

    def phonemize(self, text: str) -> tuple[str, list[int]]:
        """Convert *text* to a phoneme string and token ID sequence.

        Returns a ``(phoneme_string, token_ids)`` tuple where ``token_ids``
        is padded with 0 at start and end.  Returns ``("", [])`` for empty
        input.
        """
        if not text or not text.strip():
            return "", []

        phonemes = self._phonemes_for_text(text)
        token_ids = self._ids_from_phonemes(phonemes)
        return phonemes, token_ids

    def phonemize_long(self, text: str) -> list[tuple[str, list[int]]]:
        """Phonemize *text* and split it to stay within the 512-token limit.

        Returns a list of ``(phoneme_string, token_ids)`` tuples, one per
        chunk.
        """
        if not text or not text.strip():
            return []

        # Split into sentences and accumulate until the limit is reached.
        sentences = _SENTENCE_BOUNDARY.split(text.strip())
        chunks: list[tuple[str, list[int]]] = []
        current_sentences: list[str] = []

        for sentence in sentences:
            if not sentence.strip():
                continue

            candidate = " ".join(current_sentences + [sentence])
            if self._token_count(candidate) > _MAX_TOKENS and current_sentences:
                # Flush the current accumulation before adding the new sentence.
                flush_text = " ".join(current_sentences)
                ph = self._phonemes_for_text(flush_text)
                for chunk in self._split_phonemes_to_limit(ph, _MAX_TOKENS):
                    chunks.append((chunk, self._ids_from_phonemes(chunk)))
                current_sentences = [sentence]
            else:
                current_sentences.append(sentence)

        if current_sentences:
            flush_text = " ".join(current_sentences)
            for part in self._split_text_to_limit(flush_text, _MAX_TOKENS):
                ph = self._phonemes_for_text(part)
                for chunk in self._split_phonemes_to_limit(ph, _MAX_TOKENS):
                    chunks.append((chunk, self._ids_from_phonemes(chunk)))

        return chunks
