"""
E.V. Orchestrator — Main event loop and state machine.
Coordinates all components: perception, brain, tools, synthesis.
"""

import sys
import json
import asyncio
import logging
import threading
from typing import Optional
from pathlib import Path

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from core.event_bus import EventBus, EventType, Event, get_event_bus
from core.context_assembler import ContextAssembler
from memory.memory_manager import MemoryManager
from brain.llm_client import LLMClient, create_deepseek_client
from brain.llm_fallback import LLMFallbackChain
from brain.react_loop import ReActLoop
from tools.registry import ToolRegistry
from tools.python_executor import execute_python
from tools.shell_executor import execute_shell
from tools.file_manager import read_file, write_file, list_files
from tools.web_search import web_search
from tools.reminder import set_reminder, get_reminders, set_memory as set_reminder_memory
from tools.vision import take_screenshot, analyze_image
from tools.app_automation import automate_app
from synthesis.tts_engine import TTSEngine
from synthesis.audio_player import AudioPlayer
from ui.terminal_ui import TerminalUI, AgentState

logger = logging.getLogger("ev.orchestrator")


class Orchestrator:
    """
    Main orchestrator — the heart of E.V.
    
    Manages the event loop, coordinates all components,
    and handles user interactions.
    """

    def __init__(self):
        # Core components
        self.event_bus = get_event_bus()
        self.memory = MemoryManager()
        self.ui = TerminalUI()

        # Brain
        self.llm_chain = LLMFallbackChain()
        self.tool_registry = ToolRegistry()
        self.react_loop = ReActLoop(
            llm_client=self.llm_chain,
            tool_registry=self.tool_registry,
        )
        self.react_loop.set_structured_memory(self.memory.structured)
        self.context_assembler = ContextAssembler(self.memory)

        # Synthesis
        self.tts_engine = TTSEngine()
        self.audio_player = AudioPlayer()

        # Perception (lazy init — only when voice mode is active)
        self._audio_capture = None
        self._vad = None
        self._stt = None
        self._barge_in = None

        # State
        self._running = False
        self._voice_mode = False
        self._current_state = AgentState.IDLE

        # Register tools
        self._register_tools()

        # Set reminder memory reference
        set_reminder_memory(self.memory.structured)

        logger.info("Orchestrator initialized")

    def _register_tools(self):
        """Register all tools with the registry."""
        self.tool_registry.register("execute_python", execute_python, "Execute Python code")
        self.tool_registry.register("execute_shell", execute_shell, "Execute shell command")
        self.tool_registry.register("read_file", read_file, "Read file contents")
        self.tool_registry.register("write_file", write_file, "Write to file")
        self.tool_registry.register("list_files", list_files, "List directory contents")
        self.tool_registry.register("web_search", web_search, "Search the web")
        self.tool_registry.register("set_reminder", set_reminder, "Set a reminder")
        self.tool_registry.register("get_reminders", get_reminders, "Get reminders")
        self.tool_registry.register("take_screenshot", take_screenshot, "Take screenshot")
        self.tool_registry.register("analyze_image", analyze_image, "Analyze image")
        self.tool_registry.register("automate_app", automate_app, "Automate app")
        
        # Memory tools
        self.tool_registry.register(
            "remember_fact",
            self._remember_fact_handler,
            "Remember a fact",
        )
        self.tool_registry.register(
            "recall_facts",
            self._recall_facts_handler,
            "Recall facts from memory",
        )

        # Load schemas
        self.tool_registry.load_schemas()
        
        logger.info(f"Registered {len(self.tool_registry.list_tools())} tools")

    async def _remember_fact_handler(self, fact: str, category: str = "general") -> str:
        """Handler for remember_fact tool."""
        await self.memory.remember(fact, category=category)
        return f"Remembered: [{category}] {fact}"

    async def _recall_facts_handler(self, query: str, category: str = None) -> str:
        """Handler for recall_facts tool."""
        memories = await self.memory.recall(query, top_k=5)
        if not memories:
            return "No relevant memories found."
        
        lines = []
        for m in memories:
            relevance = f"{m['relevance']:.0%}"
            lines.append(f"- ({relevance}) {m['text']}")
        return "\n".join(lines)

    def _set_state(self, state: str):
        """Update the current agent state."""
        self._current_state = state
        self.ui.print_status(state)

    async def process_text_input(self, text: str):
        """Process a text input from the user."""
        # Handle slash commands
        if text.startswith("/"):
            await self._handle_command(text)
            return

        self.ui.print_user_input(text, source="text")
        self._set_state(AgentState.THINKING)

        # Add to memory
        self.memory.add_user_message(text)

        # Assemble context
        messages = await self.context_assembler.assemble_with_recall(text)

        # Get tool schemas
        tools = self.tool_registry.get_schemas()

        # ReAct loop
        async def on_thinking(iteration):
            if iteration > 1:
                self._set_state(f"🧠 Thinking (step {iteration})...")

        async def on_tool_call(tool_name, args):
            self._set_state(AgentState.TOOL_EXECUTING)
            self.ui.print_tool_call(tool_name, args)

        async def on_tool_result(tool_name, result):
            self.ui.print_tool_result(tool_name, result)

        try:
            response_text, updated_messages = await self.react_loop.run(
                messages=messages,
                tools=tools,
                on_thinking=on_thinking,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )
        except Exception as e:
            response_text = f"Xin lỗi, tôi gặp lỗi: {e}"
            logger.error(f"ReAct loop error: {e}", exc_info=True)

        # Display response
        self.ui.print_response(response_text)

        # Save assistant response to memory
        self.memory.add_assistant_message(response_text)

        # TTS if voice mode is active
        if self._voice_mode:
            await self._speak(response_text)

        self._set_state(AgentState.IDLE)

        # Async: save to long-term memory (non-blocking)
        asyncio.create_task(self._async_memory_save(text, response_text))

    async def _speak(self, text: str):
        """Convert text to speech and play it."""
        self._set_state(AgentState.SPEAKING)

        try:
            # Mute mic during playback (barge-in phase 1)
            if self._barge_in:
                self._barge_in.on_playback_start()

            audio = await self.tts_engine.synthesize(text)
            if audio is not None:
                await self.audio_player.play_async(audio, self.tts_engine.sample_rate)

            if self._barge_in:
                self._barge_in.on_playback_end()

        except Exception as e:
            logger.error(f"TTS/playback error: {e}")

    async def _async_memory_save(self, user_input: str, response: str):
        """Async save conversation to long-term memory."""
        try:
            # Simple heuristic: save if conversation seems important
            combined = f"User: {user_input}\nE.V.: {response}"
            if len(combined) > 100:  # Skip very short exchanges
                await self.memory.remember(
                    combined,
                    category="conversation",
                    metadata={"type": "conversation_turn"},
                )
        except Exception as e:
            logger.debug(f"Memory save error (non-critical): {e}")

    async def _handle_command(self, command: str):
        """Handle slash commands."""
        cmd = command.strip().lower()

        if cmd in ("/help", "/h"):
            self.ui.print_help()
        elif cmd in ("/quit", "/exit", "/q"):
            self.shutdown()
        elif cmd == "/clear":
            self.memory.short_term.clear()
            self.ui.print_info("Conversation cleared")
        elif cmd == "/stats":
            stats = self.memory.get_stats()
            llm_stats = self.llm_chain.get_status()
            tool_stats = self.tool_registry.get_stats()
            
            self.ui.print_info(f"Memory: {json.dumps(stats, indent=2)}")
            self.ui.print_info(f"LLM: {llm_stats['active']} ({llm_stats['providers'][0]['usage']})")
            self.ui.print_info(f"TTS: {self.tts_engine.current_engine}")
        elif cmd == "/voice":
            self._voice_mode = not self._voice_mode
            status = "ON 🎤" if self._voice_mode else "OFF ⌨️"
            self.ui.print_info(f"Voice mode: {status}")
            if self._voice_mode:
                self._init_voice()
        elif cmd.startswith("/tts "):
            engine_name = cmd.split(" ", 1)[1].strip()
            result = self.tts_engine.switch_engine(engine_name)
            self.ui.print_info(result)
        elif cmd == "/tts":
            result = self.tts_engine.cycle_engine()
            self.ui.print_info(result)
        else:
            self.ui.print_info(f"Unknown command: {command}. Type /help for available commands.")

    def _init_voice(self):
        """Initialize voice components (lazy)."""
        try:
            from perception.audio_capture import AudioCapture
            from perception.vad import VoiceActivityDetector
            from perception.stt import SpeechToText
            from perception.barge_in import BargeInController

            if not self._audio_capture:
                self._audio_capture = AudioCapture()
            if not self._vad:
                self._vad = VoiceActivityDetector()
                self._vad.initialize()
            if not self._stt:
                self._stt = SpeechToText()
                self._stt.initialize()
            if not self._barge_in:
                self._barge_in = BargeInController(
                    audio_capture=self._audio_capture,
                    audio_player=self.audio_player,
                )

            self.ui.print_info("Voice components initialized")
        except Exception as e:
            self.ui.print_error(f"Voice init failed: {e}")
            self._voice_mode = False

    async def _voice_loop(self):
        """Background voice listening loop."""
        if not self._voice_mode or not self._audio_capture:
            return

        from perception.vad import VADState

        self._audio_capture.start()
        self.ui.print_info("Voice loop started — listening...")

        try:
            while self._running and self._voice_mode:
                chunk = self._audio_capture.get_chunk(timeout=0.05)
                if chunk is None:
                    await asyncio.sleep(0.01)
                    continue

                state = self._vad.process_chunk(chunk)

                if state == VADState.SPEECH_START:
                    self._set_state(AgentState.LISTENING)

                elif state == VADState.SPEECH_END:
                    # Get accumulated audio
                    audio_buffer = self._vad.get_audio_buffer()
                    self._vad.clear_buffer()

                    if len(audio_buffer) > 0:
                        # Transcribe
                        self._set_state(AgentState.THINKING)
                        text, lang, confidence = self._stt.transcribe(audio_buffer)

                        if text.strip():
                            self.ui.print_user_input(text, source="voice")

                            # Check for wake word (if not always-on)
                            if config.ACTIVATION_MODE == "wake_word":
                                if config.WAKE_WORD.lower() not in text.lower():
                                    self._set_state(AgentState.IDLE)
                                    continue
                                # Remove wake word from text
                                text = text.lower().replace(config.WAKE_WORD.lower(), "").strip()

                            if text:
                                await self.process_text_input(text)
                        else:
                            self._set_state(AgentState.IDLE)

        except Exception as e:
            logger.error(f"Voice loop error: {e}")
        finally:
            self._audio_capture.stop()

    async def run(self):
        """Main run loop."""
        self._running = True
        self.ui.initialize()
        self.ui.print_banner()

        # Print config summary
        config.print_config_summary()

        # Validate config
        errors = config.validate_config()
        if errors:
            for err in errors:
                self.ui.print_error(err)
            self.ui.print_info("Please set up your .env file. See .env.example")
            return

        self.ui.print_help()
        self._set_state(AgentState.IDLE)

        # Start voice loop in background if voice mode is active
        voice_task = None
        if self._voice_mode:
            self._init_voice()
            voice_task = asyncio.create_task(self._voice_loop())

        # Start event bus queue processor
        bus_task = asyncio.create_task(self.event_bus.process_queue())

        # Main text input loop
        try:
            while self._running:
                try:
                    # Use asyncio-compatible input
                    text = await asyncio.get_event_loop().run_in_executor(
                        None, self.ui.get_text_input
                    )
                    
                    if text.strip():
                        await self.process_text_input(text.strip())

                except (EOFError, KeyboardInterrupt):
                    break
                except Exception as e:
                    self.ui.print_error(str(e))

        finally:
            self.shutdown()
            if voice_task:
                voice_task.cancel()
            bus_task.cancel()

    def shutdown(self):
        """Graceful shutdown."""
        self._running = False
        self.event_bus.stop()
        self.memory.close()
        
        if self._audio_capture and self._audio_capture.is_running:
            self._audio_capture.stop()

        self.ui.print_info("E.V. signing off! Bye bye! 👋🕷️")
