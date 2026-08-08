"""
E.V. Structured Memory — SQLite for structured data, logs, preferences.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger("ev.memory.structured")


class StructuredMemory:
    """
    SQLite-backed structured storage for:
    - Conversation logs
    - User preferences
    - Reminders
    - Tool usage audit trail
    """

    def __init__(self, db_path: str = "./data/ev_memory.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"SQLite database initialized at {db_path}")

    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self._conn.cursor()

        # Conversation log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_calls TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Reminders
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                due_time DATETIME NOT NULL,
                is_completed BOOLEAN DEFAULT FALSE,
                is_notified BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tool usage log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                arguments TEXT,
                result TEXT,
                success BOOLEAN,
                duration_ms INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Facts / knowledge extracted from conversations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Enable FTS5 for full-text search on conversations
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts
            USING fts5(content, content='conversations', content_rowid='id')
        """)

        self._conn.commit()
        logger.debug("Database tables created/verified")

    # ===== Conversation Log =====

    def log_message(self, session_id: str, role: str, content: str,
                    tool_calls: Optional[List] = None):
        """Log a conversation message."""
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
            (session_id, role, content, json.dumps(tool_calls) if tool_calls else None),
        )
        self._conn.commit()

        # Update FTS index
        try:
            cursor.execute(
                "INSERT INTO conversations_fts(rowid, content) VALUES (?, ?)",
                (cursor.lastrowid, content),
            )
            self._conn.commit()
        except Exception:
            pass  # FTS update failure is non-critical

    def search_conversations(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Full-text search across conversation history."""
        cursor = self._conn.cursor()
        try:
            import re
            words = re.findall(r'\w+', query)
            if not words:
                return []
            safe_query = " OR ".join(f'"{w}"' for w in words)
            cursor.execute("""
                SELECT c.* FROM conversations c
                JOIN conversations_fts fts ON c.id = fts.rowid
                WHERE conversations_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (safe_query, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"FTS search error: {e}")
            return []

    # ===== User Preferences =====

    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO preferences (key, value, updated_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), datetime.now().isoformat()),
        )
        self._conn.commit()
        logger.debug(f"Preference set: {key} = {value}")

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return json.loads(row["value"])
        return default

    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT key, value FROM preferences")
        return {row["key"]: json.loads(row["value"]) for row in cursor.fetchall()}

    # ===== Reminders =====

    def add_reminder(self, title: str, due_time: datetime,
                     description: str = "") -> int:
        """Add a reminder."""
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT INTO reminders (title, description, due_time) VALUES (?, ?, ?)",
            (title, description, due_time.isoformat()),
        )
        self._conn.commit()
        logger.info(f"Reminder added: {title} @ {due_time}")
        return cursor.lastrowid

    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        """Get all pending (not completed, not notified) reminders that are due."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM reminders
            WHERE is_completed = FALSE AND is_notified = FALSE
            AND due_time <= ?
            ORDER BY due_time
        """, (datetime.now().isoformat(),))
        return [dict(row) for row in cursor.fetchall()]

    def get_upcoming_reminders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get upcoming reminders."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM reminders
            WHERE is_completed = FALSE
            ORDER BY due_time
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]

    def complete_reminder(self, reminder_id: int):
        """Mark a reminder as completed."""
        cursor = self._conn.cursor()
        cursor.execute(
            "UPDATE reminders SET is_completed = TRUE WHERE id = ?",
            (reminder_id,),
        )
        self._conn.commit()

    def mark_notified(self, reminder_id: int):
        """Mark a reminder as notified."""
        cursor = self._conn.cursor()
        cursor.execute(
            "UPDATE reminders SET is_notified = TRUE WHERE id = ?",
            (reminder_id,),
        )
        self._conn.commit()

    # ===== Tool Log =====

    def log_tool_usage(self, tool_name: str, arguments: Dict, result: str,
                       success: bool, duration_ms: int):
        """Log a tool execution for audit."""
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT INTO tool_log (tool_name, arguments, result, success, duration_ms) VALUES (?, ?, ?, ?, ?)",
            (tool_name, json.dumps(arguments), result[:1000], success, duration_ms),
        )
        self._conn.commit()

    # ===== Facts =====

    def add_fact(self, category: str, content: str, source: str = "",
                 confidence: float = 1.0):
        """Store a fact extracted from conversation."""
        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT INTO facts (category, content, source, confidence) VALUES (?, ?, ?, ?)",
            (category, content, source, confidence),
        )
        self._conn.commit()
        logger.debug(f"Fact stored: [{category}] {content[:50]}")

    def get_facts(self, category: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get stored facts, optionally filtered by category."""
        cursor = self._conn.cursor()
        if category:
            cursor.execute(
                "SELECT * FROM facts WHERE category = ? ORDER BY created_at DESC LIMIT ?",
                (category, limit),
            )
        else:
            cursor.execute(
                "SELECT * FROM facts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        return [dict(row) for row in cursor.fetchall()]

    # ===== Cleanup =====

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            logger.info("SQLite connection closed")
