"""
E.V. Audio Player — Streaming audio playback with interrupt support.
"""

import logging
import threading
import queue
import numpy as np
from typing import Optional

logger = logging.getLogger("ev.synthesis.audio_player")


class AudioPlayer:
    """
    Audio playback with streaming and interrupt capability.
    Plays audio chunks as they arrive, can be stopped immediately.
    """

    def __init__(self, sample_rate: int = 24000):
        self.sample_rate = sample_rate
        self._stream = None
        self._playing = False
        self._stop_event = threading.Event()
        self._audio_queue: queue.Queue = queue.Queue()

    def play(self, audio_data: np.ndarray, sample_rate: int = None):
        """Play audio data (blocking)."""
        rate = sample_rate or self.sample_rate
        
        try:
            import sounddevice as sd
            
            self._playing = True
            self._stop_event.clear()
            
            # Play in chunks so we can interrupt
            chunk_size = int(rate * 0.1)  # 100ms chunks
            total_samples = len(audio_data)
            
            stream = sd.OutputStream(
                samplerate=rate,
                channels=1,
                dtype="float32",
            )
            stream.start()
            
            offset = 0
            while offset < total_samples and not self._stop_event.is_set():
                end = min(offset + chunk_size, total_samples)
                chunk = audio_data[offset:end]
                stream.write(chunk.reshape(-1, 1))
                offset = end
            
            stream.stop()
            stream.close()
            self._playing = False

        except ImportError:
            logger.error("sounddevice not installed")
        except Exception as e:
            logger.error(f"Playback error: {e}")
            self._playing = False

    async def play_async(self, audio_data: np.ndarray, sample_rate: int = None):
        """Play audio in a background thread (non-blocking)."""
        import asyncio
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.play, audio_data, sample_rate)

    def stop(self):
        """Stop playback immediately."""
        self._stop_event.set()
        self._playing = False
        logger.debug("Playback stopped")

    @property
    def is_playing(self) -> bool:
        return self._playing
