# E.V. Agent — Enhanced Virtual Assistant 🕷️🤖

> An intelligent, multi-provider AI assistant inspired by **E.V. from Spider-Man: Brand New Day (2026)**. Featuring a ReAct (Reasoning & Acting) loop, voice & text perception, multi-LLM fallback chain (OpenRouter, Groq, Gemini, DeepSeek), tool execution, and long-term memory.

---

## ✨ Features

- **🧠 Multi-Provider LLM Engine**:
  - **OpenRouter** (Primary): Access to `google/gemini-2.0-flash-001`, `claude-3.7-sonnet`, `gpt-4o`, `deepseek-chat`, and 100+ AI models via a single API key.
  - **Fallback Chain**: Automatic failover (`OpenRouter → Groq → Gemini → DeepSeek`) ensuring 99.9% uptime.
- **🔄 ReAct Loop**: Autonomous Reasoning → Acting → Observation cycle for multi-step tool use and complex problem solving.
- **🎙️ Perception (STT & VAD)**:
  - Voice Activity Detection (VAD) via Silero VAD.
  - Speech-to-Text (STT) powered by Faster-Whisper.
  - Hybrid activation modes: Hotkey (`Ctrl+Space`), Wake Word ("Hey EV"), or Always-On.
- **🔊 Speech Synthesis (TTS)**:
  - Multi-engine TTS supporting EdgeTTS (default Vietnamese neural voice `vi-VN-HoaiMyNeural`), Kokoro, and Piper.
- **💾 Memory System**:
  - Short-term conversation history buffer.
  - Long-term memory powered by ChromaDB (vector embeddings) & SQLite.
- **🛠️ Built-in Tools**:
  - `execute_python`: Sandboxed Python execution.
  - `execute_shell`: System shell commands execution.
  - `web_search`: Live web searching.
  - `read_file` / `write_file` / `list_files`: File system management.
  - `take_screenshot` / `analyze_image`: Vision capabilities.
  - `automate_app`: Desktop application automation.
  - `set_reminder` / `get_reminders`: Task scheduling and reminders.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- `git` installed
- (Optional) `ffmpeg` for advanced audio playback

### 2. Installation

Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/ev-agent.git
cd ev-agent
```

Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and fill in your API key(s):
```env
# === Primary LLM (OpenRouter) ===
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemini-2.0-flash-001

# === Optional Fallback LLMs ===
GROQ_API_KEY=
GEMINI_API_KEY=
DEEPSEEK_API_KEY=
```

---

## 💻 Usage

### Run in Text Mode (Interactive Terminal)
```bash
python main.py
```

### Run with Voice Mode Enabled
```bash
python main.py --voice
```

### Check Configuration
```bash
python main.py --config
```

### In-App Commands
- `/voice`: Toggle Voice mode ON/OFF
- `/tts [engine]`: Switch TTS engine (`edge`, `kokoro`, `piper`)
- `/stats`: Display memory, LLM usage, and TTS status
- `/clear`: Clear short-term conversation memory
- `/help`: Show command help
- `/quit`: Exit E.V. Agent

---

## 🏗️ Project Architecture

```
ev-agent/
├── brain/               # LLM clients, fallback chain, ReAct loop
├── core/                # Orchestrator, context assembler, event bus
├── memory/              # ChromaDB vector store, SQLite structured memory
├── perception/          # Audio capture, VAD, STT (Whisper)
├── synthesis/           # TTS engines (EdgeTTS, Kokoro, Piper), Audio player
├── tools/               # Tool registry & execution (Python, Shell, Files, Web, Vision)
├── ui/                  # Rich Terminal UI
├── config.py            # Global configuration & environment loader
├── main.py              # Application entry point
├── .env.example         # Environment template
└── requirements.txt     # Dependencies
```

---

## 🛡️ License

MIT License. See `LICENSE` for details.
