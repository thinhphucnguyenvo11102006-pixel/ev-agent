#!/usr/bin/env python3
"""
E.V. — Enhanced Virtual Assistant
Inspired by E.V. from Spider-Man: Brand New Day (2026)

Usage:
    python main.py              # Start in text mode
    python main.py --voice      # Start with voice mode
    python main.py --tts edge   # Specify TTS engine
"""

import sys
import asyncio
import logging
import argparse
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # File handler
    log_dir = PROJECT_ROOT / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    log_file = log_dir / f"ev_{datetime.now().strftime('%Y%m%d')}.log"

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler() if verbose else logging.NullHandler(),
        ],
    )

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="E.V. — Enhanced Virtual Assistant (Spider-Man: Brand New Day)"
    )
    parser.add_argument(
        "--voice", "-v",
        action="store_true",
        help="Start with voice mode enabled",
    )
    parser.add_argument(
        "--tts",
        choices=["kokoro", "piper", "edge"],
        default=None,
        help="TTS engine to use (default: from config)",
    )
    parser.add_argument(
        "--verbose", "-V",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--config",
        action="store_true",
        help="Show current configuration and exit",
    )
    return parser.parse_args()


async def main():
    """Main entry point."""
    # Force UTF-8 on Windows
    if sys.platform == "win32":
        import os
        os.system("chcp 65001 > nul 2>&1")
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()

    # Setup logging
    setup_logging(verbose=args.verbose)

    # Import config (loads .env)
    import config

    # Show config and exit
    if args.config:
        config.print_config_summary()
        errors = config.validate_config()
        if errors:
            print("\n⚠️  Configuration errors:")
            for err in errors:
                print(f"  - {err}")
        return

    # Override TTS if specified
    if args.tts:
        config.DEFAULT_TTS_ENGINE = args.tts

    # Create and run orchestrator
    from core.orchestrator import Orchestrator

    orchestrator = Orchestrator()

    if args.voice:
        orchestrator._voice_mode = True

    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        orchestrator.shutdown()
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n[FATAL] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Windows asyncio event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
