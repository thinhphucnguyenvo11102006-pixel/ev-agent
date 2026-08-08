"""
E.V. Barge-in Controller — Handles user interruptions during playback.
Phase 1: Simple mute/unmute approach.
"""

import logging
from typing import Optional

logger = logging.getLogger("ev.perception.barge_in")


class BargeInController:
    """
    Controls barge-in (user interrupting E.V. while speaking).
    
    Phase 1 (Simple): Mute mic during TTS playback to avoid self-hearing.
    Phase 2 (Future): AEC-based approach for true full-duplex.
    """

    def __init__(self, audio_capture=None, audio_player=None):
        self._audio_capture = audio_capture
        self._audio_player = audio_player
        self._is_playing = False
        self._interrupted = False

    def set_audio_capture(self, capture):
        """Set the audio capture reference."""
        self._audio_capture = capture

    def set_audio_player(self, player):
        """Set the audio player reference."""
        self._audio_player = player

    def on_playback_start(self):
        """Called when TTS playback starts."""
        self._is_playing = True
        self._interrupted = False
        
        # Phase 1: Mute mic during playback
        if self._audio_capture:
            self._audio_capture.mute()
        
        logger.debug("Playback started, mic muted")

    def on_playback_end(self):
        """Called when TTS playback finishes."""
        self._is_playing = False
        
        # Unmute mic
        if self._audio_capture:
            self._audio_capture.unmute()
            self._audio_capture.clear_queue()  # Clear any buffered audio
        
        logger.debug("Playback ended, mic unmuted")

    def interrupt(self):
        """Signal that the user wants to interrupt."""
        if not self._is_playing:
            return

        self._interrupted = True
        
        # Stop audio playback
        if self._audio_player:
            self._audio_player.stop()

        # Unmute mic
        if self._audio_capture:
            self._audio_capture.unmute()
            self._audio_capture.clear_queue()

        logger.info("⚡ Barge-in triggered! Playback interrupted.")

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def was_interrupted(self) -> bool:
        return self._interrupted
