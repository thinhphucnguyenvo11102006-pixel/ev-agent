"""
E.V. VAD — Voice Activity Detection using Silero VAD.
Detects speech onset and offset from audio stream.
"""

import logging
import numpy as np
from enum import Enum, auto
from typing import Optional

import config

logger = logging.getLogger("ev.perception.vad")


class VADState(Enum):
    """VAD state machine states."""
    IDLE = auto()           # No speech detected
    SPEECH_START = auto()   # Speech just started
    SPEAKING = auto()       # Currently speaking
    SPEECH_END = auto()     # Speech just ended


class VoiceActivityDetector:
    """
    Silero VAD wrapper with state machine for dynamic endpointing.
    
    State transitions:
    IDLE → SPEECH_START → SPEAKING → SPEECH_END → IDLE
    """

    def __init__(
        self,
        threshold: float = None,
        silence_duration_ms: int = None,
        speech_min_duration_ms: int = None,
        sample_rate: int = None,
    ):
        self.threshold = threshold or config.VAD_THRESHOLD
        self.silence_duration_ms = silence_duration_ms or config.SILENCE_DURATION_MS
        self.speech_min_duration_ms = speech_min_duration_ms or config.SPEECH_MIN_DURATION_MS
        self.sample_rate = sample_rate or config.SAMPLE_RATE

        self._model = None
        self._state = VADState.IDLE
        self._speech_chunks = 0
        self._silence_chunks = 0
        self._chunk_duration_ms = config.AUDIO_CHUNK_MS
        self._audio_buffer = []

        self._initialized = False

    def initialize(self):
        """Load the Silero VAD model."""
        if self._initialized:
            return

        try:
            import torch
            
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=True,
            )
            self._model = model
            self._initialized = True
            logger.info("✓ Silero VAD model loaded")

        except ImportError:
            logger.warning("torch not installed, trying silero-vad package...")
            try:
                from silero_vad import load_silero_vad
                self._model = load_silero_vad(onnx=True)
                self._initialized = True
                logger.info("✓ Silero VAD model loaded (via silero-vad package)")
            except ImportError:
                logger.error("Neither torch nor silero-vad installed. VAD disabled.")
        except Exception as e:
            logger.error(f"Failed to load VAD model: {e}")

    def process_chunk(self, audio_chunk: np.ndarray) -> VADState:
        """
        Process an audio chunk and return the current VAD state.
        
        Args:
            audio_chunk: Float32 numpy array of audio samples
            
        Returns:
            Current VADState
        """
        if not self._initialized:
            self.initialize()
        
        if not self._model:
            return VADState.IDLE

        try:
            import torch

            # Ensure correct format
            if audio_chunk.dtype != np.float32:
                audio_chunk = audio_chunk.astype(np.float32)

            tensor = torch.from_numpy(audio_chunk)
            
            # Get speech probability
            speech_prob = self._model(tensor, self.sample_rate).item()

            # State machine logic
            is_speech = speech_prob >= self.threshold

            if self._state == VADState.IDLE:
                if is_speech:
                    self._state = VADState.SPEECH_START
                    self._speech_chunks = 1
                    self._silence_chunks = 0
                    self._audio_buffer = [audio_chunk]
                    logger.debug(f"Speech detected (prob={speech_prob:.2f})")

            elif self._state in (VADState.SPEECH_START, VADState.SPEAKING):
                self._audio_buffer.append(audio_chunk)
                
                if is_speech:
                    self._speech_chunks += 1
                    self._silence_chunks = 0
                    self._state = VADState.SPEAKING
                else:
                    self._silence_chunks += 1
                    silence_ms = self._silence_chunks * self._chunk_duration_ms

                    if silence_ms >= self.silence_duration_ms:
                        # Check minimum speech duration
                        speech_ms = self._speech_chunks * self._chunk_duration_ms
                        if speech_ms >= self.speech_min_duration_ms:
                            self._state = VADState.SPEECH_END
                            logger.debug(
                                f"Speech ended (duration={speech_ms}ms, "
                                f"silence={silence_ms}ms)"
                            )
                        else:
                            # Too short, treat as noise
                            self._state = VADState.IDLE
                            self._audio_buffer.clear()
                            logger.debug(f"Speech too short ({speech_ms}ms), ignoring")

            elif self._state == VADState.SPEECH_END:
                # Reset for next utterance
                self._state = VADState.IDLE
                self._speech_chunks = 0
                self._silence_chunks = 0

            return self._state

        except Exception as e:
            logger.error(f"VAD processing error: {e}")
            return VADState.IDLE

    def get_audio_buffer(self) -> np.ndarray:
        """Get the accumulated audio buffer (the detected speech)."""
        if self._audio_buffer:
            return np.concatenate(self._audio_buffer)
        return np.array([], dtype=np.float32)

    def clear_buffer(self):
        """Clear the audio buffer."""
        self._audio_buffer.clear()
        self._speech_chunks = 0
        self._silence_chunks = 0

    def reset(self):
        """Reset the VAD state."""
        self._state = VADState.IDLE
        self.clear_buffer()
        if self._model and hasattr(self._model, 'reset_states'):
            self._model.reset_states()

    @property
    def state(self) -> VADState:
        return self._state
