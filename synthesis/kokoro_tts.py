"""
E.V. Kokoro TTS — Local high-quality text-to-speech.
"""

import logging
import numpy as np
from typing import Optional

import config

logger = logging.getLogger("ev.synthesis.kokoro")


class KokoroTTS:
    """
    Kokoro TTS wrapper.
    82M parameter model, runs efficiently on CPU.
    """

    def __init__(self, voice: str = None):
        self.voice = voice or config.KOKORO_VOICE
        self._pipeline = None
        self._initialized = False
        self.sample_rate = 24000

    def initialize(self):
        """Load the Kokoro model."""
        if self._initialized:
            return

        try:
            from kokoro import KPipeline

            self._pipeline = KPipeline(lang_code="a")  # Auto-detect language
            self._initialized = True
            logger.info(f"✓ Kokoro TTS loaded (voice: {self.voice})")

        except ImportError:
            logger.error("kokoro not installed. Run: pip install kokoro")
        except Exception as e:
            logger.error(f"Failed to load Kokoro TTS: {e}")

    def synthesize(self, text: str) -> Optional[np.ndarray]:
        """
        Convert text to speech.
        Returns float32 numpy array of audio samples.
        """
        if not self._initialized:
            self.initialize()

        if not self._pipeline:
            return None

        try:
            # Generate audio
            generator = self._pipeline(text, voice=self.voice)
            
            audio_parts = []
            for gs, ps, audio in generator:
                audio_parts.append(audio)

            if audio_parts:
                full_audio = np.concatenate(audio_parts)
                logger.debug(f"Kokoro generated {len(full_audio)} samples ({len(full_audio)/self.sample_rate:.1f}s)")
                return full_audio

            return None

        except Exception as e:
            logger.error(f"Kokoro synthesis error: {e}")
            return None

    def is_ready(self) -> bool:
        return self._initialized and self._pipeline is not None
