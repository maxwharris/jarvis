"""
Configuration management for Jarvis AI Assistant.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration."""
    name: str = "Jarvis"
    version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"


@dataclass
class ModelConfig:
    """AI model configuration."""
    text_model: str = "qwen2.5:14b"
    vision_model: str = "llava:13b"
    embedding_model: str = "nomic-embed-text"
    ollama_host: str = "http://localhost:11434"
    max_tokens: int = 4096
    temperature: float = 0.7
    context_window: int = 8192


@dataclass
class VoiceConfig:
    """Voice processing configuration."""
    enabled: bool = True
    wake_word: str = "hey max"
    wake_word_engine: str = "openwakeword"
    stt_engine: str = "faster-whisper"
    stt_model: str = "base"
    tts_engine: str = "silero"
    tts_voice: str = "en_v6"
    audio_device: Optional[str] = None
    sample_rate: int = 16000
    chunk_size: int = 1024
    silence_threshold: float = 0.01
    silence_duration: float = 2.0


@dataclass
class InputConfig:
    """Input configuration."""
    hotkey: str = "ctrl+alt+j"
    popup_timeout: int = 30
    max_input_length: int = 1000


@dataclass
class OutputConfig:
    """Output configuration."""
    speak_responses: bool = True
    show_notifications: bool = True
    response_timeout: int = 30


@dataclass
class PrivacyConfig:
    """Privacy and security configuration."""
    online_mode: bool = False
    confirm_dangerous_actions: bool = True
    log_conversations: bool = True
    encrypt_logs: bool = False
    auto_delete_logs_days: int = 30


@dataclass
class FileManagementConfig:
    """File management configuration."""
    allowed_extensions: list = field(default_factory=lambda: [
        ".txt", ".pdf", ".docx", ".jpg", ".png", ".gif", ".mp4", ".mp3"
    ])
    max_file_size_mb: int = 100
    backup_before_operations: bool = True
    safe_directories: list = field(default_factory=lambda: [
        "~/Documents", "~/Downloads", "~/Desktop"
    ])


@dataclass
class WebSearchConfig:
    """Web search configuration."""
    search_engine: str = "duckduckgo"
    max_results: int = 5
    timeout: int = 10
    user_agent: str = "Jarvis AI Assistant 1.0"


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "logs/jarvis.db"
    backup_interval_hours: int = 24
    max_backup_files: int = 7


@dataclass
class UIConfig:
    """UI configuration."""
    theme: str = "dark"
    system_tray: bool = True
    startup_notification: bool = True
    minimize_to_tray: bool = True


@dataclass
class PerformanceConfig:
    """Performance configuration."""
    max_concurrent_tasks: int = 3
    cache_size_mb: int = 512
    gpu_acceleration: bool = True
    cpu_threads: Optional[int] = None


class Config:
    """Main configuration class for Jarvis AI Assistant."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to configuration file. If None, uses default.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.models_config_path = self._get_models_config_path()
        
        # Initialize configuration sections
        self.app = AppConfig()
        self.models = ModelConfig()
        self.voice = VoiceConfig()
        self.input = InputConfig()
        self.output = OutputConfig()
        self.privacy = PrivacyConfig()
        self.file_management = FileManagementConfig()
        self.web_search = WebSearchConfig()
        self.database = DatabaseConfig()
        self.ui = UIConfig()
        self.performance = PerformanceConfig()
        
        # Load configuration
        self.load_config()
        self.load_models_config()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        # Try to find config relative to project root
        current_dir = Path(__file__).parent.parent.parent.parent
        config_file = current_dir / "config" / "settings.yaml"
        
        if config_file.exists():
            return str(config_file)
        
        # Fallback to user config directory
        config_dir = Path.home() / ".jarvis"
        config_dir.mkdir(exist_ok=True)
        return str(config_dir / "settings.yaml")
    
    def _get_models_config_path(self) -> str:
        """Get models configuration file path."""
        config_dir = Path(self.config_path).parent
        return str(config_dir / "models.yaml")
    
    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found: {self.config_path}")
                self.save_config()  # Create default config
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                logger.warning("Empty configuration file, using defaults")
                return
            
            # Update configuration sections
            self._update_config_section(self.app, config_data.get('app', {}))
            self._update_config_section(self.models, config_data.get('models', {}))
            self._update_config_section(self.voice, config_data.get('voice', {}))
            self._update_config_section(self.input, config_data.get('input', {}))
            self._update_config_section(self.output, config_data.get('output', {}))
            self._update_config_section(self.privacy, config_data.get('privacy', {}))
            self._update_config_section(self.file_management, config_data.get('file_management', {}))
            self._update_config_section(self.web_search, config_data.get('web_search', {}))
            self._update_config_section(self.database, config_data.get('database', {}))
            self._update_config_section(self.ui, config_data.get('ui', {}))
            self._update_config_section(self.performance, config_data.get('performance', {}))
            
            logger.info(f"Configuration loaded from {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Using default configuration")
    
    def load_models_config(self) -> None:
        """Load models configuration from file."""
        try:
            if not os.path.exists(self.models_config_path):
                logger.warning(f"Models config file not found: {self.models_config_path}")
                return
            
            with open(self.models_config_path, 'r', encoding='utf-8') as f:
                self.models_data = yaml.safe_load(f)
            
            logger.info(f"Models configuration loaded from {self.models_config_path}")
            
        except Exception as e:
            logger.error(f"Error loading models configuration: {e}")
            self.models_data = {}
    
    def _update_config_section(self, config_obj: Any, config_data: Dict[str, Any]) -> None:
        """Update configuration section with data from file."""
        for key, value in config_data.items():
            if hasattr(config_obj, key):
                setattr(config_obj, key, value)
            else:
                logger.warning(f"Unknown configuration key: {key}")
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        try:
            # Ensure config directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            config_data = {
                'app': self._dataclass_to_dict(self.app),
                'models': self._dataclass_to_dict(self.models),
                'voice': self._dataclass_to_dict(self.voice),
                'input': self._dataclass_to_dict(self.input),
                'output': self._dataclass_to_dict(self.output),
                'privacy': self._dataclass_to_dict(self.privacy),
                'file_management': self._dataclass_to_dict(self.file_management),
                'web_search': self._dataclass_to_dict(self.web_search),
                'database': self._dataclass_to_dict(self.database),
                'ui': self._dataclass_to_dict(self.ui),
                'performance': self._dataclass_to_dict(self.performance),
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def _dataclass_to_dict(self, obj: Any) -> Dict[str, Any]:
        """Convert dataclass to dictionary."""
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith('_'):
                result[key] = value
        return result
    
    def get_model_info(self, model_type: str, model_name: str) -> Dict[str, Any]:
        """Get information about a specific model.
        
        Args:
            model_type: Type of model (text_models, vision_models, etc.)
            model_name: Name of the model
            
        Returns:
            Model information dictionary
        """
        if not hasattr(self, 'models_data'):
            return {}
        
        models = self.models_data.get(model_type, {})
        return models.get(model_name, {})
    
    def get_performance_profile(self, profile_name: str) -> Dict[str, Any]:
        """Get performance profile configuration.
        
        Args:
            profile_name: Name of the performance profile
            
        Returns:
            Performance profile configuration
        """
        if not hasattr(self, 'models_data'):
            return {}
        
        profiles = self.models_data.get('performance_profiles', {})
        return profiles.get(profile_name, {})
    
    def is_online_mode(self) -> bool:
        """Check if online mode is enabled."""
        return self.privacy.online_mode
    
    def toggle_online_mode(self) -> bool:
        """Toggle online mode and return new state."""
        self.privacy.online_mode = not self.privacy.online_mode
        self.save_config()
        return self.privacy.online_mode
    
    def get_database_path(self) -> str:
        """Get absolute path to database file."""
        if os.path.isabs(self.database.path):
            return self.database.path
        
        # Relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        return str(project_root / self.database.path)
    
    def validate_config(self) -> bool:
        """Validate configuration settings.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Validate required settings
            if not self.models.ollama_host:
                logger.error("Ollama host not configured")
                return False
            
            if self.models.max_tokens <= 0:
                logger.error("Invalid max_tokens value")
                return False
            
            if self.voice.sample_rate <= 0:
                logger.error("Invalid sample_rate value")
                return False
            
            # Validate file paths
            db_dir = os.path.dirname(self.get_database_path())
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


# Global configuration instance
config = Config()
