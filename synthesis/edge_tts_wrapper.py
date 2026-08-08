"""
E.V. Edge-TTS — Microsoft Edge cloud text-to-speech.
High quality voices, requires internet.
"""

import logging
import asyncio
import io
import numpy as np
from typing import Optional

import config

logger = logging.getLogger("ev.synthesis.edge_tts")


class EdgeTTSEngine:
    """
    Edge-TTS wrapper using Microsoft's cloud TTS service.
    Highest quality voices, but requires internet connection.
    """

    def __init__(self, voice: str = None):
        self.voice = voice or config.EDGE_TTS_VOICE
        self._initialized = False
        self.sample_rate = 24000  # Edge-TTS outputs 24kHz by default

    def initialize(self):
        """Check if edge-tts is available."""
        if self._initialized:
            return

        try:
            import edge_tts
            self._initialized = True
            logger.info(f"✓ Edge-TTS loaded (voice: {self.voice})")
        except ImportError:
            logger.error("edge-tts not installed. Run: pip install edge-tts")

    async def synthesize_async(self, text: str) -> Optional[np.ndarray]:
        """
        Convert text to speech using Edge-TTS (async).
        Returns float32 numpy array.
        """
        if not self._initialized:
            self.initialize()

        if not self._initialized:
            return None

        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice)
            
            audio_data = io.BytesIO()
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.write(chunk["data"])

            audio_data.seek(0)
            
            # Parse MP3 data to numpy array
            audio_array = self._mp3_to_numpy(audio_data.read())
            
            if audio_array is not None:
                logger.debug(
                    f"Edge-TTS generated {len(audio_array)} samples "
                    f"({len(audio_array)/self.sample_rate:.1f}s)"
                )
            
            return audio_array

        except Exception as e:
            logger.error(f"Edge-TTS synthesis error: {e}")
            return None

    def synthesize(self, text: str) -> Optional[np.ndarray]:
        """Synchronous wrapper for synthesize_async."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run, self.synthesize_async(text)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self.synthesize_async(text))
        except RuntimeError:
            return asyncio.run(self.synthesize_async(text))

    def _mp3_to_numpy(self, mp3_data: bytes) -> Optional[np.ndarray]:
        """Convert MP3 bytes to numpy array."""
        try:
            # Try using pydub
            from pydub import AudioSegment
            
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
            audio = audio.set_channels(1)
            self.sample_rate = audio.frame_rate
            
            samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
            samples = samples / 32768.0  # Normalize to [-1, 1]
            
            return samples

        except ImportError:
            # Fallback: save to temp file and use soundfile
            try:
                import tempfile
                import soundfile as sf
                
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(mp3_data)
                    f.flush()
                    audio, sr = sf.read(f.name)
                    self.sample_rate = sr
                    return audio.astype(np.float32)
            except Exception:
                logger.error("Cannot decode MP3. Install pydub: pip install pydub")
                return None

    async def list_voices(self, language: str = "vi") -> list:
        """List available voices for a language."""
        try:
            import edge_tts
            voices = await edge_tts.list_voices()
            return [
                {"name": v["ShortName"], "gender": v["Gender"], "locale": v["Locale"]}
                for v in voices
                if v["Locale"].startswith(language)
            ]
        except Exception as e:
            logger.error(f"Error listing voices: {e}")
            return []

    def is_ready(self) -> bool:
        return self._initialized
