"""
E.V. STT — Speech-to-Text using Faster-Whisper.
Transcribes audio to text with language detection.
"""

import logging
import numpy as np
from typing import Optional, Tuple

import config

logger = logging.getLogger("ev.perception.stt")


class SpeechToText:
    """
    Faster-Whisper based speech recognition.
    Features:
    - Auto language detection (Vietnamese / English)
    - INT8 quantization for speed
    - Configurable model size
    """

    def __init__(
        self,
        model_name: str = None,
        device: str = None,
        compute_type: str = None,
    ):
        self.model_name = model_name or config.WHISPER_MODEL
        self.device = device or config.WHISPER_DEVICE
        self.compute_type = compute_type or config.WHISPER_COMPUTE_TYPE
        
        self._model = None
        self._initialized = False

    def initialize(self):
        """Load the Whisper model."""
        if self._initialized:
            return

        try:
            from faster_whisper import WhisperModel

            # Auto-detect device
            if self.device == "auto":
                try:
                    import torch
                    self.device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    self.device = "cpu"

            logger.info(
                f"Loading Whisper model: {self.model_name} "
                f"(device={self.device}, compute={self.compute_type})"
            )

            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            self._initialized = True
            logger.info("✓ Faster-Whisper model loaded")

        except ImportError:
            logger.error("faster-whisper not installed. Run: pip install faster-whisper")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")

    def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
    ) -> Tuple[str, str, float]:
        """
        Transcribe audio to text.
        
        Args:
            audio: Float32 numpy array at 16kHz
            language: Force language (None = auto-detect)
            
        Returns:
            Tuple of (text, detected_language, confidence)
        """
        if not self._initialized:
            self.initialize()

        if self._model is None:
            return "", "unknown", 0.0

        try:
            # Ensure float32
            if audio.dtype != np.float32:
                audio = audio.astype(np.float32)

            # Normalize if needed
            if np.max(np.abs(audio)) > 1.0:
                audio = audio / np.max(np.abs(audio))

            segments, info = self._model.transcribe(
                audio,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200,
                ),
            )

            # Collect all segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            full_text = " ".join(text_parts).strip()
            detected_lang = info.language if info else "unknown"
            confidence = info.language_probability if info else 0.0

            if full_text:
                logger.info(
                    f"Transcribed ({detected_lang}, {confidence:.0%}): {full_text[:100]}"
                )
            
            return full_text, detected_lang, confidence

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return "", "unknown", 0.0

    def is_ready(self) -> bool:
        """Check if the model is loaded and ready."""
        return self._initialized and self._model is not None
