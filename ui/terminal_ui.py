"""
E.V. Terminal UI — Rich terminal interface with status, transcript, and controls.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("ev.ui.terminal")


class AgentState:
    """Possible agent states."""
    IDLE = "💤 Idle"
    LISTENING = "🎤 Listening..."
    THINKING = "🧠 Thinking..."
    SPEAKING = "🔊 Speaking..."
    TOOL_EXECUTING = "🛠️ Executing tool..."
    ERROR = "❌ Error"
    STARTING = "⚡ Starting..."


class TerminalUI:
    """
    Rich terminal UI for E.V. Agent.
    Shows status, conversation, and tool execution logs.
    """

    def __init__(self):
        self._console = None
        self._state = AgentState.STARTING
        self._initialized = False
        self.initialize()

    def initialize(self):
        """Initialize Rich console."""
        if self._initialized:
            return

        try:
            import sys
            import os

            # Force UTF-8 on Windows to prevent UnicodeEncodeError with emoji
            if sys.platform == "win32":
                os.system("chcp 65001 > nul 2>&1")
                if hasattr(sys.stdout, "reconfigure"):
                    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                if hasattr(sys.stderr, "reconfigure"):
                    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

            from rich.console import Console
            from rich.theme import Theme

            theme = Theme({
                "ev": "bold cyan",
                "user": "bold green",
                "tool": "bold yellow",
                "error": "bold red",
                "info": "dim",
                "status": "bold magenta",
            })

            self._console = Console(theme=theme, force_terminal=True)
            self._initialized = True
        except ImportError:
            # Fallback to basic print
            self._console = None
            self._initialized = True

    def print_banner(self):
        """Print the E.V. startup banner."""
        self.initialize()

        banner = """
╔══════════════════════════════════════════════════════╗
║                                                      ║
║     ███████╗  ██╗   ██╗                              ║
║     ██╔════╝  ██║   ██║     Enhanced Virtual         ║
║     █████╗    ██║   ██║       Assistant              ║
║     ██╔══╝    ╚██╗ ██╔╝                              ║
║     ███████╗   ╚████╔╝    Spider-Man: Brand New Day  ║
║     ╚══════╝    ╚═══╝                                ║
║                                                      ║
║  🕷️  "Hey, I'm E.V.! Ready to help!" 🕸️              ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
"""
        if self._console:
            self._console.print(banner, style="cyan")
        else:
            print(banner)

    def print_status(self, state: str):
        """Print current agent state."""
        self._state = state
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if self._console:
            self._console.print(f"[info][{timestamp}][/info] [status]{state}[/status]")
        else:
            print(f"[{timestamp}] {state}")

    def print_user_input(self, text: str, source: str = "text"):
        """Print user input."""
        icon = "🎤" if source == "voice" else "⌨️"
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if self._console:
            self._console.print(
                f"[info][{timestamp}][/info] {icon} [user]You:[/user] {text}"
            )
        else:
            print(f"[{timestamp}] {icon} You: {text}")

    def print_response(self, text: str, streaming: bool = False):
        """Print E.V.'s response."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if streaming:
            # For streaming, print without newline
            if self._console:
                self._console.print(text, end="", style="ev")
            else:
                print(text, end="", flush=True)
        else:
            if self._console:
                self._console.print(
                    f"[info][{timestamp}][/info] 🤖 [ev]E.V.:[/ev] {text}"
                )
            else:
                print(f"[{timestamp}] 🤖 E.V.: {text}")

    def print_response_start(self):
        """Print the start of a response (for streaming)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self._console:
            self._console.print(
                f"[info][{timestamp}][/info] 🤖 [ev]E.V.:[/ev] ", end=""
            )
        else:
            print(f"[{timestamp}] 🤖 E.V.: ", end="", flush=True)

    def print_response_end(self):
        """Print the end of a streaming response."""
        print()  # Newline

    def print_tool_call(self, tool_name: str, args: str = ""):
        """Print tool execution info."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if self._console:
            self._console.print(
                f"[info][{timestamp}][/info] 🛠️ [tool]Tool:[/tool] {tool_name}({args[:80]})"
            )
        else:
            print(f"[{timestamp}] 🛠️ Tool: {tool_name}({args[:80]})")

    def print_tool_result(self, tool_name: str, result: str):
        """Print tool execution result."""
        # Truncate long results
        display_result = result[:200] + "..." if len(result) > 200 else result
        
        if self._console:
            self._console.print(
                f"  [info]↳ Result:[/info] {display_result}", style="dim"
            )
        else:
            print(f"  ↳ Result: {display_result}")

    def print_error(self, message: str):
        """Print an error message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if self._console:
            self._console.print(
                f"[info][{timestamp}][/info] [error]❌ Error: {message}[/error]"
            )
        else:
            print(f"[{timestamp}] ❌ Error: {message}")

    def print_info(self, message: str):
        """Print an info message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if self._console:
            self._console.print(
                f"[info][{timestamp}] ℹ️  {message}[/info]"
            )
        else:
            print(f"[{timestamp}] ℹ️  {message}")

    def print_help(self):
        """Print help/controls."""
        help_text = """
┌─────────────── Controls ───────────────┐
│  Ctrl+Space  : Push-to-talk (voice)    │
│  Ctrl+T      : Switch TTS engine       │
│  Ctrl+C      : Exit                    │
│  /help       : Show this help          │
│  /voice      : Toggle voice mode       │
│  /tts <name> : Switch TTS engine       │
│  /clear      : Clear conversation      │
│  /stats      : Show memory stats       │
│  /quit       : Exit E.V.              │
└────────────────────────────────────────┘
"""
        if self._console:
            self._console.print(help_text, style="dim")
        else:
            print(help_text)

    def get_text_input(self, prompt: str = "You > ") -> str:
        """Get text input from user."""
        if self._console:
            return self._console.input(f"[green]{prompt}[/green]")
        else:
            return input(prompt)
