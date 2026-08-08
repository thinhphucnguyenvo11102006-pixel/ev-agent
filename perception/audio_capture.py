"""
E.V. Audio Capture — Microphone input streaming.
Uses sounddevice for real-time audio capture.
"""

import logging
import threading
import queue
import numpy as np
from typing import Optional, Callable

import config

logger = logging.getLogger("ev.perception.audio_capture")


class AudioCapture:
    """
    Real-time microphone audio capture.
    Streams audio chunks to a callback or queue.
    """

    def __init__(
        self,
        sample_rate: int = None,
        channels: int = None,
        chunk_ms: int = None,
    ):
        self.sample_rate = sample_rate or config.SAMPLE_RATE
        self.channels = channels or config.CHANNELS
        self.chunk_ms = chunk_ms or config.AUDIO_CHUNK_MS
        self.chunk_size = int(self.sample_rate * self.chunk_ms / 1000)

        self._stream = None
        self._running = False
        self._audio_queue: queue.Queue = queue.Queue()
        self._muted = False

        logger.info(
            f"AudioCapture configured: {self.sample_rate}Hz, "
            f"{self.channels}ch, {self.chunk_ms}ms chunks ({self.chunk_size} samples)"
        )

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback invoked by sounddevice for each audio chunk."""
        if status:
            logger.warning(f"Audio status: {status}")
        
        if not self._muted:
            # Convert to float32 numpy array
            audio_data = np.copy(indata[:, 0]) if self.channels == 1 else np.copy(indata)
            self._audio_queue.put(audio_data)

    def start(self):
        """Start audio capture."""
        if self._running:
            return

        try:
            import sounddevice as sd
            import sys

            # Try to use WASAPI on Windows to avoid MME -9999 errors
            if sys.platform == 'win32':
                try:
                    wasapi_info = next((api for api in sd.query_hostapis() if 'WASAPI' in api['name']), None)
                    if wasapi_info:
                        sd.default.hostapi = wasapi_info['name']
                        logger.info(f"Using host API: {wasapi_info['name']}")
                except Exception as ex:
                    logger.debug(f"Could not set WASAPI: {ex}")

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                blocksize=self.chunk_size,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._running = True
            logger.info("🎤 Audio capture started")

        except ImportError:
            logger.error("sounddevice not installed. Run: pip install sounddevice")
            raise
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            raise

    def stop(self):
        """Stop audio capture."""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        logger.info("🎤 Audio capture stopped")

    def get_chunk(self, timeout: float = 0.1) -> Optional[np.ndarray]:
        """Get the next audio chunk from the queue."""
        try:
            return self._audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def mute(self):
        """Mute the microphone (for barge-in)."""
        self._muted = True
        logger.debug("🔇 Mic muted")

    def unmute(self):
        """Unmute the microphone."""
        self._muted = False
        logger.debug("🔊 Mic unmuted")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_muted(self) -> bool:
        return self._muted

    def clear_queue(self):
        """Clear any buffered audio."""
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
