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
    """Custom log handler that writes to SQLite database with robust error handling."""
    
    def __init__(self, db_path: str):
        super().__init__()
        self.db_path = db_path
        self.db_available = False
        self.init_attempts = 0
        self.max_init_attempts = 3
        self._init_database()
    
    def _validate_database(self) -> bool:
        """Validate that the database file is a valid SQLite database."""
        try:
            if not os.path.exists(self.db_path):
                return False
            
            # Check file size - SQLite databases are at least 1024 bytes
            if os.path.getsize(self.db_path) < 1024:
                print(f"Database file too small ({os.path.getsize(self.db_path)} bytes), likely corrupted")
                return False
            
            # Try to open and query the database
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                cursor.fetchone()
                return True
                
        except sqlite3.DatabaseError as e:
            print(f"Database validation failed: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error validating database: {e}")
            return False
    
    def _backup_corrupted_database(self):
        """Backup corrupted database file before recreating."""
        try:
            if os.path.exists(self.db_path):
                backup_path = f"{self.db_path}.corrupted.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(self.db_path, backup_path)
                print(f"Corrupted database backed up to: {backup_path}")
        except Exception as e:
            print(f"Could not backup corrupted database: {e}")
            # Try to remove the corrupted file
            try:
                os.remove(self.db_path)
                print("Removed corrupted database file")
            except Exception as e2:
                print(f"Could not remove corrupted database: {e2}")
    
    def _init_database(self):
        """Initialize the logging database with robust error handling."""
        self.init_attempts += 1
        
        try:
            # Check if database exists and is valid
            if os.path.exists(self.db_path) and not self._validate_database():
                print("Database file is corrupted, attempting recovery...")
                self._backup_corrupted_database()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create/initialize database with timeout
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                # Enable WAL mode for better concurrent access
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.execute("PRAGMA mmap_size=268435456")  # 256MB
                
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
                
                # Create indexes for faster queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_logs_timestamp 
                    ON logs(timestamp)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_logs_level 
                    ON logs(level)
                """)
                
                # Test write to ensure database is working
                conn.execute("""
                    INSERT INTO logs (timestamp, level, logger, message)
                    VALUES (?, 'INFO', 'system', 'Database initialized successfully')
                """, (datetime.now().isoformat(),))
                
                conn.commit()
                
                # Validate the database was created properly
                if self._validate_database():
                    self.db_available = True
                    print("Database logging initialized successfully")
                else:
                    raise sqlite3.DatabaseError("Database validation failed after creation")
                
        except Exception as e:
            print(f"Error initializing log database (attempt {self.init_attempts}): {e}")
            self.db_available = False
            
            # Retry initialization if we haven't exceeded max attempts
            if self.init_attempts < self.max_init_attempts:
                print(f"Retrying database initialization... ({self.init_attempts}/{self.max_init_attempts})")
                import time
                time.sleep(1)  # Brief delay before retry
                self._init_database()
            else:
                print("Database logging disabled due to initialization failures")
    
    def emit(self, record):
        """Emit a log record to the database with robust error handling."""
        # Skip database logging if it's not available
        if not self.db_available:
            return
        
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
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
                
        except sqlite3.DatabaseError as e:
            # Database-specific error - might be corruption
            if "file is not a database" in str(e).lower() or "database disk image is malformed" in str(e).lower():
                print(f"Database corruption detected: {e}")
                print("Attempting to recover database...")
                self.db_available = False
                self._init_database()  # Try to recover
            else:
                # Other database errors - disable database logging temporarily
                print(f"Database error (disabling database logging): {e}")
                self.db_available = False
                
        except Exception as e:
            # Other errors - log but don't disable database logging
            if "Error writing to log database" not in str(e):  # Avoid recursive error messages
                print(f"Error writing to log database: {e}")


class ConversationLogger:
    """Logger for conversation history with robust error handling."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db_available = True
        self._init_database()
    
    def _init_database(self):
        """Initialize the conversation database with robust error handling."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                # Enable WAL mode for better concurrent access
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                
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
                self.db_available = True
                
        except Exception as e:
            print(f"Error initializing conversation database: {e}")
            self.db_available = False
    
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
