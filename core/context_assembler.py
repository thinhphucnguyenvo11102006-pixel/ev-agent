"""
E.V. Context Assembler — Builds the consolidated prompt for the LLM.
Combines system prompt, memory context, tools, and conversation history.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from memory.memory_manager import MemoryManager

logger = logging.getLogger("ev.core.context_assembler")


class ContextAssembler:
    """
    Builds the complete prompt for the LLM by combining:
    1. System prompt (E.V. persona)
    2. Memory context (preferences, facts, relevant memories)
    3. Current datetime
    4. Conversation history (short-term memory)
    """

    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Load the system prompt from file."""
        prompt_path = Path(__file__).parent.parent / "brain" / "prompts" / "system_prompt.md"
        try:
            return prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}")
            return "You are E.V., a helpful and cheerful AI assistant."

    def build_system_message(self, user_input: str = "") -> str:
        """
        Build the complete system message with context.
        """
        parts = [self._system_prompt]

        # Add current datetime
        now = datetime.now()
        parts.append(f"\n## Thông tin hiện tại\n- Ngày giờ: {now.strftime('%Y-%m-%d %H:%M:%S (%A)')}")

        # Add memory context
        memory_context = self.memory.get_context_for_prompt(user_input)
        if memory_context:
            parts.append(f"\n## Context từ Memory\n{memory_context}")

        return "\n".join(parts)

    def assemble(self, user_input: str = "") -> List[Dict[str, Any]]:
        """
        Assemble the full message list for the LLM.
        
        Returns:
            List of messages in OpenAI format
        """
        # Update system message with fresh context
        system_content = self.build_system_message(user_input)
        self.memory.short_term.set_system_message(system_content)

        # Get all messages (system + conversation history)
        messages = self.memory.get_messages()

        logger.debug(f"Assembled {len(messages)} messages for LLM")
        return messages

    async def assemble_with_recall(self, user_input: str) -> List[Dict[str, Any]]:
        """
        Assemble messages with long-term memory recall.
        Searches for relevant memories and injects them into context.
        """
        # Skip recall for short/trivial greetings to optimize speed & token usage
        cleaned_input = user_input.strip().lower()
        words = cleaned_input.split()
        trivial_greetings = {"chào", "chào bạn", "hi", "hello", "xin chào", "bạn tên gì", "bạn là ai", "ok", "cảm ơn", "bye"}
        
        memories = []
        if len(words) >= 4 or not any(g in cleaned_input for g in trivial_greetings):
            memories = await self.memory.recall(user_input, top_k=3)

        # Build system message
        parts = [self._system_prompt]

        # Datetime
        now = datetime.now()
        parts.append(f"\n## Thông tin hiện tại\n- Ngày giờ: {now.strftime('%Y-%m-%d %H:%M:%S (%A)')}")

        # Memory context
        memory_context = self.memory.get_context_for_prompt(user_input)
        if memory_context:
            parts.append(f"\n## Context từ Memory\n{memory_context}")

        # Recalled memories (only high relevance > 0.5)
        if memories:
            memory_lines = []
            for m in memories:
                if m.get("relevance", 0) >= 0.5:
                    memory_lines.append(f"- {m['text']}")
            if memory_lines:
                parts.append(
                    "\n## Relevant Memories\n" + "\n".join(memory_lines)
                )

        system_content = "\n".join(parts)
        self.memory.short_term.set_system_message(system_content)

        return self.memory.get_messages()
