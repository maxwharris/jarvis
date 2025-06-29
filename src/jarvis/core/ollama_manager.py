"""
Ollama Manager for Jarvis AI Assistant.
Handles Ollama service management, model detection, and auto-startup.
"""

import subprocess
import time
import requests
import json
import asyncio
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import threading
import psutil

from .config import config
from .logging import get_logger

logger = get_logger("ollama_manager")


class OllamaManager:
    """Manages Ollama service and models."""
    
    def __init__(self):
        self.ollama_host = config.models.ollama_host
        self.is_running = False
        self.available_models = []
        self.ollama_process = None
        self.startup_timeout = 30  # seconds
    
    async def initialize(self) -> bool:
        """Initialize Ollama manager and ensure service is running."""
        try:
            logger.info("Initializing Ollama manager...")
            
            # Check if Ollama is already running
            if await self.check_ollama_status():
                logger.info("Ollama is already running")
                self.is_running = True
            else:
                logger.info("Ollama not running, attempting to start...")
                if await self.start_ollama():
                    logger.info("Ollama started successfully")
                    self.is_running = True
                else:
                    logger.error("Failed to start Ollama")
                    return False
            
            # Check for available models
            await self.refresh_models()
            
            # Validate we have at least one model
            if not self.available_models:
                logger.warning("No models found! User needs to download models.")
                return False
            
            logger.info(f"Ollama manager initialized with {len(self.available_models)} models")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Ollama manager: {e}")
            return False
    
    async def check_ollama_status(self) -> bool:
        """Check if Ollama service is running."""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    async def start_ollama(self) -> bool:
        """Start Ollama service."""
        try:
            # First, check if ollama command is available
            if not self.is_ollama_installed():
                logger.error("Ollama is not installed or not in PATH")
                return False
            
            # Try to start Ollama service
            logger.info("Starting Ollama service...")
            
            # Start ollama serve in background
            try:
                self.ollama_process = subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                # Wait for service to start
                for i in range(self.startup_timeout):
                    await asyncio.sleep(1)
                    if await self.check_ollama_status():
                        logger.info("Ollama service started successfully")
                        return True
                    
                    # Check if process died
                    if self.ollama_process.poll() is not None:
                        stdout, stderr = self.ollama_process.communicate()
                        logger.error(f"Ollama process died: {stderr.decode()}")
                        return False
                
                logger.error("Ollama service failed to start within timeout")
                return False
                
            except Exception as e:
                logger.error(f"Failed to start Ollama process: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error starting Ollama: {e}")
            return False
    
    def is_ollama_installed(self) -> bool:
        """Check if Ollama is installed and accessible."""
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    async def refresh_models(self) -> List[Dict]:
        """Refresh list of available models."""
        try:
            if not await self.check_ollama_status():
                logger.warning("Ollama not running, cannot refresh models")
                return []
            
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.available_models = data.get('models', [])
                
                logger.info(f"Found {len(self.available_models)} available models:")
                for model in self.available_models:
                    name = model.get('name', 'Unknown')
                    size = model.get('size', 0)
                    size_gb = size / (1024**3) if size > 0 else 0
                    logger.info(f"  - {name} ({size_gb:.1f}GB)")
                
                return self.available_models
            else:
                logger.error(f"Failed to get models: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error refreshing models: {e}")
            return []
    
    def get_best_model(self) -> Optional[str]:
        """Get the best available model for text generation."""
        if not self.available_models:
            return None
        
        # Priority order for models (best to worst)
        preferred_models = [
            "qwen2.5:14b",
            "qwen2.5:7b", 
            "llama3.1:8b",
            "llama3:8b",
            "llama2:13b",
            "llama2:7b",
            "llama2",
            "mistral:7b",
            "mistral",
            "codellama:7b",
            "codellama"
        ]
        
        # Check for exact matches first
        available_names = [model.get('name', '') for model in self.available_models]
        
        for preferred in preferred_models:
            if preferred in available_names:
                logger.info(f"Selected model: {preferred}")
                return preferred
        
        # If no preferred model found, use the first available
        if available_names:
            first_model = available_names[0]
            logger.info(f"Using first available model: {first_model}")
            return first_model
        
        return None
    
    def get_vision_model(self) -> Optional[str]:
        """Get the best available vision model."""
        if not self.available_models:
            return None
        
        vision_models = [
            "llava:13b",
            "llava:7b", 
            "llava",
            "bakllava",
            "moondream"
        ]
        
        available_names = [model.get('name', '') for model in self.available_models]
        
        for vision_model in vision_models:
            if vision_model in available_names:
                logger.info(f"Selected vision model: {vision_model}")
                return vision_model
        
        return None
    
    async def download_recommended_model(self) -> bool:
        """Download a recommended model if none are available."""
        try:
            if not await self.check_ollama_status():
                logger.error("Ollama not running, cannot download models")
                return False
            
            # Recommend a good general-purpose model
            recommended_model = "llama2:7b"  # Good balance of performance and size
            
            logger.info(f"Downloading recommended model: {recommended_model}")
            
            # Start download process
            process = subprocess.Popen(
                ["ollama", "pull", recommended_model],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Monitor download progress
            while process.poll() is None:
                await asyncio.sleep(2)
                logger.info("Downloading model...")
            
            if process.returncode == 0:
                logger.info(f"Successfully downloaded {recommended_model}")
                await self.refresh_models()
                return True
            else:
                stdout, stderr = process.communicate()
                logger.error(f"Failed to download model: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
            return False
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """Get information about a specific model."""
        for model in self.available_models:
            if model.get('name') == model_name:
                return model
        return None
    
    async def test_model(self, model_name: str) -> bool:
        """Test if a model is working correctly."""
        try:
            if not await self.check_ollama_status():
                return False
            
            # Send a simple test prompt
            test_data = {
                "model": model_name,
                "prompt": "Hello",
                "stream": False
            }
            
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json=test_data,
                timeout=30
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error testing model {model_name}: {e}")
            return False
    
    def get_status_info(self) -> Dict:
        """Get comprehensive status information."""
        return {
            "ollama_running": self.is_running,
            "ollama_host": self.ollama_host,
            "models_available": len(self.available_models),
            "models": [model.get('name', 'Unknown') for model in self.available_models],
            "best_text_model": self.get_best_model(),
            "best_vision_model": self.get_vision_model(),
            "ollama_installed": self.is_ollama_installed()
        }
    
    def cleanup(self) -> None:
        """Cleanup Ollama manager."""
        logger.info("Cleaning up Ollama manager...")
        
        # Don't stop Ollama service as user might want to keep it running
        # Just clean up our process reference
        if self.ollama_process:
            self.ollama_process = None
        
        logger.info("Ollama manager cleanup complete")


# Utility functions for user guidance
def get_installation_instructions() -> str:
    """Get Ollama installation instructions."""
    return """
To install Ollama:

1. Visit https://ollama.ai
2. Download Ollama for your operating system
3. Install and run Ollama
4. Open a terminal and run: ollama pull llama2

Recommended models to download:
- ollama pull llama2:7b (Good general model, ~4GB)
- ollama pull qwen2.5:7b (Better performance, ~4GB)
- ollama pull llava:7b (For image analysis, ~4GB)

After installation, restart Jarvis.
"""

def get_model_recommendations() -> List[str]:
    """Get list of recommended models."""
    return [
        "llama2:7b",      # Good general purpose
        "qwen2.5:7b",     # Better performance
        "llama3.1:8b",    # Latest Llama
        "llava:7b",       # Vision capabilities
        "mistral:7b"      # Alternative option
    ]
