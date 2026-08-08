"""
E.V. TTS Engine Selector — Routes text to the appropriate TTS engine.
Supports Kokoro, Piper, and Edge-TTS with runtime switching.
"""

import logging
import numpy as np
from typing import Optional

import config
from synthesis.kokoro_tts import KokoroTTS
from synthesis.piper_tts import PiperTTS
from synthesis.edge_tts_wrapper import EdgeTTSEngine

logger = logging.getLogger("ev.synthesis.tts_engine")


class TTSEngine:
    """
    TTS engine selector and router.
    Manages multiple TTS backends and routes synthesis requests.
    """

    ENGINES = ["kokoro", "piper", "edge"]

    def __init__(self, default_engine: str = None):
        self.current_engine = default_engine or config.DEFAULT_TTS_ENGINE
        
        # Initialize all engines (lazy)
        self._engines = {
            "kokoro": KokoroTTS(),
            "piper": PiperTTS(),
            "edge": EdgeTTSEngine(),
        }

        self.sample_rate = 24000  # Will be updated by active engine
        logger.info(f"TTS Engine initialized (default: {self.current_engine})")

    def _get_engine(self, name: str = None):
        """Get a TTS engine by name."""
        engine_name = name or self.current_engine
        engine = self._engines.get(engine_name)
        if not engine:
            raise ValueError(f"Unknown TTS engine: {engine_name}")
        return engine

    async def synthesize(self, text: str, engine: str = None) -> Optional[np.ndarray]:
        """
        Synthesize text to audio using the selected engine.
        
        Args:
            text: Text to convert to speech
            engine: Override engine name (optional)
            
        Returns:
            Float32 numpy array of audio samples, or None on failure
        """
        engine_name = engine or self.current_engine
        tts = self._get_engine(engine_name)

        logger.debug(f"Synthesizing with {engine_name}: {text[:50]}...")

        try:
            # Try the selected engine
            if engine_name == "edge":
                audio = await tts.synthesize_async(text)
            else:
                # Kokoro and Piper are synchronous
                import asyncio
                loop = asyncio.get_event_loop()
                audio = await loop.run_in_executor(None, tts.synthesize, text)

            if audio is not None:
                self.sample_rate = tts.sample_rate
                return audio

            # Fallback to Edge-TTS if primary fails
            if engine_name != "edge":
                logger.warning(f"{engine_name} failed, falling back to Edge-TTS")
                edge = self._engines["edge"]
                audio = await edge.synthesize_async(text)
                if audio is not None:
                    self.sample_rate = edge.sample_rate
                    return audio

            logger.error("All TTS engines failed")
            return None

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return None

    def switch_engine(self, engine_name: str) -> str:
        """Switch the active TTS engine."""
        if engine_name not in self.ENGINES:
            return f"Unknown engine: {engine_name}. Available: {self.ENGINES}"
        
        self.current_engine = engine_name
        logger.info(f"TTS engine switched to: {engine_name}")
        return f"TTS engine switched to {engine_name}"

    def cycle_engine(self) -> str:
        """Cycle to the next TTS engine."""
        idx = self.ENGINES.index(self.current_engine)
        next_idx = (idx + 1) % len(self.ENGINES)
        return self.switch_engine(self.ENGINES[next_idx])

    def get_status(self) -> dict:
        """Get status of all TTS engines."""
        return {
            "active": self.current_engine,
            "engines": {
                name: {
                    "active": name == self.current_engine,
                    "type": "local" if name != "edge" else "cloud",
                }
                for name in self.ENGINES
            },
        }
