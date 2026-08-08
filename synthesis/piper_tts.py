"""
E.V. Piper TTS — Lightweight local text-to-speech.
"""

import logging
import subprocess
import tempfile
import numpy as np
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger("ev.synthesis.piper")


class PiperTTS:
    """
    Piper TTS wrapper.
    Very fast, optimized for CPU. Good for low-power devices.
    """

    def __init__(self, model_path: str = None):
        self.model_path = model_path or config.PIPER_MODEL_PATH
        self._initialized = False
        self.sample_rate = 22050

    def initialize(self):
        """Check if Piper is available."""
        if self._initialized:
            return

        try:
            # Try importing piper-tts Python package
            import piper
            self._initialized = True
            logger.info("✓ Piper TTS loaded")
        except ImportError:
            # Check if piper binary is available
            try:
                result = subprocess.run(
                    ["piper", "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    self._initialized = True
                    logger.info("✓ Piper TTS binary found")
                else:
                    logger.warning("Piper TTS not available")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                logger.warning("Piper TTS not installed")

    def synthesize(self, text: str) -> Optional[np.ndarray]:
        """
        Convert text to speech using Piper.
        """
        if not self._initialized:
            self.initialize()

        if not self._initialized:
            return None

        try:
            import piper

            voice = piper.PiperVoice.load(self.model_path) if self.model_path else None
            if not voice:
                logger.error("No Piper model specified")
                return None

            # Synthesize to WAV
            import io
            import wave

            audio_buffer = io.BytesIO()
            with wave.open(audio_buffer, "wb") as wav_file:
                voice.synthesize(text, wav_file)

            # Read audio data
            audio_buffer.seek(0)
            with wave.open(audio_buffer, "rb") as wav_file:
                self.sample_rate = wav_file.getframerate()
                frames = wav_file.readframes(wav_file.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

            return audio

        except Exception as e:
            logger.error(f"Piper synthesis error: {e}")
            return None

    def is_ready(self) -> bool:
        return self._initialized
