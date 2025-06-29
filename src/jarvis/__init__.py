"""
Jarvis AI Assistant - A local AI assistant with voice and text capabilities.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .core.config import Config
from .core.ai_engine import AIEngine
from .core.logging import setup_logging

__all__ = ["Config", "AIEngine", "setup_logging"]
