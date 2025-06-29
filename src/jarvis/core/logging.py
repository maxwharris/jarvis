"""
Logging system for Jarvis AI Assistant.
"""

import os
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional
import sqlite3
from contextlib import contextmanager

from .config import config


class DatabaseLogHandler(logging.Handler):
    """Custom log handler that writes to SQLite database."""
    
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the logging database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL,
                        logger TEXT NOT NULL,
                        message TEXT NOT NULL,
                        module TEXT,
                        function TEXT,
                        line_number INTEGER,
                        thread_id INTEGER,
                        process_id INTEGER
                    )
                """)
                
                # Create index for faster queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_logs_timestamp 
                    ON logs(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_logs_level 
                    ON logs(level)
                """)
                
                conn.commit()
        except Exception as e:
            print(f"Error initializing log database: {e}")
    
    def emit(self, record):
        """Emit a log record to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO logs (
                        timestamp, level, logger, message, module, 
                        function, line_number, thread_id, process_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.fromtimestamp(record.created).isoformat(),
                    record.levelname,
                    record.name,
                    self.format(record),
                    record.module if hasattr(record, 'module') else None,
                    record.funcName if hasattr(record, 'funcName') else None,
                    record.lineno if hasattr(record, 'lineno') else None,
                    record.thread if hasattr(record, 'thread') else None,
                    record.process if hasattr(record, 'process') else None
                ))
                conn.commit()
        except Exception as e:
            # Fallback to stderr if database logging fails
            print(f"Error writing to log database: {e}")
            print(f"Log record: {self.format(record)}")


class ConversationLogger:
    """Logger for conversation history."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the conversation database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        input_type TEXT NOT NULL,
                        user_input TEXT,
                        ai_response TEXT,
                        action_taken TEXT,
                        online_mode BOOLEAN,
                        model_used TEXT,
                        processing_time_ms INTEGER,
                        tokens_used INTEGER
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        total_interactions INTEGER DEFAULT 0,
                        total_tokens INTEGER DEFAULT 0
                    )
                """)
                
                # Create indexes
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_session 
                    ON conversations(session_id)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversations_timestamp 
                    ON conversations(timestamp)
                """)
                
                conn.commit()
        except Exception as e:
            print(f"Error initializing conversation database: {e}")
    
    def start_session(self, session_id: str) -> None:
        """Start a new conversation session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO sessions (id, start_time)
                    VALUES (?, ?)
                """, (session_id, datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            print(f"Error starting session: {e}")
    
    def end_session(self, session_id: str) -> None:
        """End a conversation session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update session end time and statistics
                conn.execute("""
                    UPDATE sessions 
                    SET end_time = ?,
                        total_interactions = (
                            SELECT COUNT(*) FROM conversations 
                            WHERE session_id = ?
                        ),
                        total_tokens = (
                            SELECT COALESCE(SUM(tokens_used), 0) FROM conversations 
                            WHERE session_id = ?
                        )
                    WHERE id = ?
                """, (
                    datetime.now().isoformat(),
                    session_id, session_id, session_id
                ))
                conn.commit()
        except Exception as e:
            print(f"Error ending session: {e}")
    
    def log_interaction(
        self,
        session_id: str,
        input_type: str,
        user_input: str,
        ai_response: str,
        action_taken: Optional[str] = None,
        online_mode: bool = False,
        model_used: Optional[str] = None,
        processing_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None
    ) -> None:
        """Log a conversation interaction."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO conversations (
                        session_id, timestamp, input_type, user_input,
                        ai_response, action_taken, online_mode, model_used,
                        processing_time_ms, tokens_used
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_id,
                    datetime.now().isoformat(),
                    input_type,
                    user_input,
                    ai_response,
                    action_taken,
                    online_mode,
                    model_used,
                    processing_time_ms,
                    tokens_used
                ))
                conn.commit()
        except Exception as e:
            print(f"Error logging interaction: {e}")
    
    def get_recent_conversations(
        self, 
        session_id: Optional[str] = None, 
        limit: int = 10
    ) -> list:
        """Get recent conversations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if session_id:
                    cursor = conn.execute("""
                        SELECT * FROM conversations 
                        WHERE session_id = ?
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (session_id, limit))
                else:
                    cursor = conn.execute("""
                        SELECT * FROM conversations 
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    """, (limit,))
                
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting recent conversations: {e}")
            return []
    
    def cleanup_old_logs(self, days: int = 30) -> None:
        """Clean up old conversation logs."""
        try:
            cutoff_date = datetime.now().replace(
                day=datetime.now().day - days
            ).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # Delete old conversations
                conn.execute("""
                    DELETE FROM conversations 
                    WHERE timestamp < ?
                """, (cutoff_date,))
                
                # Delete old sessions
                conn.execute("""
                    DELETE FROM sessions 
                    WHERE start_time < ?
                """, (cutoff_date,))
                
                conn.commit()
        except Exception as e:
            print(f"Error cleaning up old logs: {e}")


def setup_logging(log_level: Optional[str] = None) -> tuple:
    """Set up logging system for Jarvis.
    
    Args:
        log_level: Override log level from config
        
    Returns:
        Tuple of (logger, conversation_logger)
    """
    # Get log level from config or parameter
    level = log_level or config.app.log_level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logs directory - now database is already in logs/ so just use its parent
    log_dir = Path(config.get_database_path()).parent
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        # Fallback to current directory if we can't create logs directory
        print(f"Warning: Could not create logs directory {log_dir}: {e}")
        log_dir = Path.cwd() / "logs"
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e2:
            print(f"Warning: Could not create fallback logs directory: {e2}")
            log_dir = Path.cwd()  # Use current directory as last resort
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (rotating)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "jarvis.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Database handler (if enabled)
    if config.privacy.log_conversations:
        try:
            db_handler = DatabaseLogHandler(config.get_database_path())
            db_handler.setLevel(logging.INFO)  # Only log INFO and above to DB
            db_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(db_handler)
        except Exception as e:
            print(f"Warning: Could not set up database logging: {e}")
    
    # Set up conversation logger
    conversation_logger = None
    if config.privacy.log_conversations:
        try:
            conversation_logger = ConversationLogger(config.get_database_path())
        except Exception as e:
            print(f"Warning: Could not set up conversation logging: {e}")
    
    # Configure specific loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    
    # Create main application logger
    app_logger = logging.getLogger("jarvis")
    app_logger.info(f"Logging initialized - Level: {level}")
    
    return app_logger, conversation_logger


@contextmanager
def log_performance(logger, operation_name: str):
    """Context manager for logging operation performance."""
    start_time = datetime.now()
    try:
        yield
    finally:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() * 1000
        logger.debug(f"{operation_name} completed in {duration:.2f}ms")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(f"jarvis.{name}")
