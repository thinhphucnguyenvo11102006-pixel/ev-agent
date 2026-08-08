"""
E.V. Audio Capture — Microphone input streaming.
Uses sounddevice for real-time audio capture with automatic hardware fallback.
"""

import sys
import logging
import threading
import queue
import numpy as np
from typing import Optional, Callable

import config

logger = logging.getLogger("ev.perception.audio_capture")


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int = 16000) -> np.ndarray:
    """Resample float32 audio array from orig_sr to target_sr."""
    if orig_sr == target_sr or len(audio) == 0:
        return audio
    try:
        from scipy import signal
        num_samples = int(round(len(audio) * target_sr / orig_sr))
        return signal.resample(audio, num_samples).astype(np.float32)
    except Exception:
        # Fallback linear interpolation using numpy
        duration = len(audio) / orig_sr
        orig_times = np.linspace(0, duration, len(audio), endpoint=False)
        target_count = int(round(duration * target_sr))
        new_times = np.linspace(0, duration, target_count, endpoint=False)
        return np.interp(new_times, orig_times, audio).astype(np.float32)


class AudioCapture:
    """
    Real-time microphone audio capture.
    Streams audio chunks to a queue with auto-fallback for hardware sample rates.
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
        self.actual_sample_rate = self.sample_rate

        logger.info(
            f"AudioCapture configured: {self.sample_rate}Hz, "
            f"{self.channels}ch, {self.chunk_ms}ms chunks ({self.chunk_size} samples)"
        )

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback invoked by sounddevice for each audio chunk."""
        if status:
            logger.warning(f"Audio status: {status}")
        
        if not self._muted:
            audio_data = np.copy(indata[:, 0]) if self.channels == 1 else np.copy(indata)
            
            # Resample if actual sample rate differs from target 16kHz
            if self.actual_sample_rate != self.sample_rate:
                audio_data = resample_audio(audio_data, self.actual_sample_rate, self.sample_rate)

            self._audio_queue.put(audio_data)

    def start(self):
        """Start audio capture with automatic device and sample rate detection."""
        if self._running:
            return

        try:
            import sounddevice as sd

            devices = sd.query_devices()
            default_input = sd.default.device[0]
            logger.info(f"Available input devices count: {len(devices)}, default input index: {default_input}")

            native_sr = 44100
            if default_input is not None and default_input >= 0 and default_input < len(devices):
                dev_info = devices[default_input]
                native_sr = int(dev_info.get("default_samplerate", 44100))
                logger.info(f"Default mic: '{dev_info.get('name')}', native rate: {native_sr}Hz")

            # Try sample rates: [16000, native_sr, 48000, 44100]
            rates_to_try = [self.sample_rate]
            if native_sr not in rates_to_try:
                rates_to_try.append(native_sr)
            for fallback_sr in [48000, 44100]:
                if fallback_sr not in rates_to_try:
                    rates_to_try.append(fallback_sr)

            last_error = None
            for sr in rates_to_try:
                try:
                    blocksize = int(sr * self.chunk_ms / 1000)
                    logger.info(f"Attempting mic InputStream with samplerate={sr}Hz, blocksize={blocksize}...")
                    
                    self._stream = sd.InputStream(
                        samplerate=sr,
                        channels=self.channels,
                        dtype="float32",
                        blocksize=blocksize,
                        callback=self._audio_callback,
                    )
                    self._stream.start()
                    self.actual_sample_rate = sr
                    self._running = True
                    logger.info(f"🎤 Audio capture successfully started ({sr}Hz {'native' if sr == self.sample_rate else 'resampled to 16kHz'})")
                    return
                except Exception as ex:
                    last_error = ex
                    logger.warning(f"Could not open microphone at {sr}Hz: {ex}")

            raise RuntimeError(f"Could not open microphone on any sample rate ({rates_to_try}): {last_error}")

        except ImportError:
            logger.error("sounddevice not installed. Run: pip install sounddevice")
            raise
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            self._running = False
            raise

    def stop(self):
        """Stop audio capture."""
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.debug(f"Error closing audio stream: {e}")
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

    def unmute(self):
        """Unmute the microphone."""
        self._muted = False

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
