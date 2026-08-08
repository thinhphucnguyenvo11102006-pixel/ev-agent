"""
E.V. Agent Configuration
All settings are loaded from environment variables or .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# ===== Project Paths =====
PROJECT_ROOT = Path(__file__).parent.resolve()
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_DB_PATH = str(DATA_DIR / "chroma_db")
SQLITE_DB_PATH = str(DATA_DIR / "ev_memory.db")
AUDIO_CACHE_DIR = str(DATA_DIR / "audio_cache")

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "chroma_db").mkdir(exist_ok=True)
(DATA_DIR / "audio_cache").mkdir(exist_ok=True)

# ===== LLM: OpenRouter =====
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# ===== LLM: DeepSeek =====
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

# ===== LLM: Fallback =====
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# ===== Perception: STT =====
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")  # "cuda" / "cpu" / "auto"
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# ===== Perception: VAD =====
VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", "0.5"))
SILENCE_DURATION_MS = int(os.getenv("SILENCE_DURATION_MS", "800"))
SPEECH_MIN_DURATION_MS = int(os.getenv("SPEECH_MIN_DURATION_MS", "250"))

# ===== Audio =====
SAMPLE_RATE = 16000
CHANNELS = 1
AUDIO_CHUNK_MS = 30  # 30ms chunks for VAD

# ===== TTS =====
DEFAULT_TTS_ENGINE = os.getenv("DEFAULT_TTS_ENGINE", "edge")  # "kokoro" / "piper" / "edge"
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "vi-VN-HoaiMyNeural")
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "af_heart")
PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "")

# ===== Memory =====
MAX_SHORT_TERM_MESSAGES = int(os.getenv("MAX_SHORT_TERM_MESSAGES", "20"))
MEMORY_TOP_K = int(os.getenv("MEMORY_TOP_K", "5"))

# ===== Safety =====
ALLOWED_DIRECTORIES = os.getenv(
    "ALLOWED_DIRECTORIES",
    str(Path.home() / "Documents") + ";" + str(Path.home() / "Desktop")
).split(";")
DANGEROUS_COMMANDS = [
    "rm -rf", "format", "del /f /s", "shutdown", "restart",
    "rmdir /s", "reg delete", "bcdedit", "diskpart"
]
MAX_REACT_ITERATIONS = int(os.getenv("MAX_REACT_ITERATIONS", "5"))
TOOL_EXECUTION_TIMEOUT = int(os.getenv("TOOL_EXECUTION_TIMEOUT", "30"))

# ===== Activation =====
ACTIVATION_MODE = os.getenv("ACTIVATION_MODE", "hybrid")  # "hotkey" / "always_on" / "wake_word" / "hybrid"
HOTKEY = os.getenv("HOTKEY", "ctrl+space")
WAKE_WORD = os.getenv("WAKE_WORD", "hey ev")

# ===== E.V. Persona =====
EV_NAME = "E.V."
EV_PERSONALITY = "cheerful"  # vui vẻ, thân thiện


def validate_config():
    """Validate that required configuration is set."""
    errors = []
    if not (OPENROUTER_API_KEY or GROQ_API_KEY or GEMINI_API_KEY or DEEPSEEK_API_KEY):
        errors.append("No API key set. Please set OPENROUTER_API_KEY, GROQ_API_KEY, GEMINI_API_KEY, or DEEPSEEK_API_KEY in .env file.")
    return errors


def print_config_summary():
    """Print a summary of the current configuration."""
    import sys
    import io
    
    # Force UTF-8 output on Windows
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    from rich.console import Console
    from rich.table import Table

    console = Console(force_terminal=True)
    table = Table(title="E.V. Configuration", show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("OpenRouter", f"{OPENROUTER_MODEL} ({'✓ Configured' if OPENROUTER_API_KEY else '✗ Not Set'})")
    table.add_row("LLM Fallbacks", f"Groq({'✓' if GROQ_API_KEY else '✗'}) / Gemini({'✓' if GEMINI_API_KEY else '✗'}) / DeepSeek({'✓' if DEEPSEEK_API_KEY else '✗'})")
    table.add_row("Whisper Model", f"{WHISPER_MODEL} ({WHISPER_COMPUTE_TYPE})")
    table.add_row("Whisper Device", WHISPER_DEVICE)
    table.add_row("TTS Engine", DEFAULT_TTS_ENGINE)
    table.add_row("Activation", ACTIVATION_MODE)
    table.add_row("Memory", f"Short: {MAX_SHORT_TERM_MESSAGES} msgs | Long: ChromaDB + SQLite")
    table.add_row("Data Dir", str(DATA_DIR))

    console.print(table)
