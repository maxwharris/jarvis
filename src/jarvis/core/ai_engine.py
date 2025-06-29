"""
Core AI Engine for Jarvis AI Assistant.
Handles interactions with local LLMs via Ollama.
"""

import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Union, AsyncGenerator
from datetime import datetime
import requests
from PIL import Image
import base64
import io

from .config import config
from .logging import get_logger, log_performance

logger = get_logger("ai_engine")


class OllamaClient:
    """Client for interacting with Ollama API."""
    
    def __init__(self, host: str = None):
        self.host = host or config.models.ollama_host
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Jarvis-AI-Assistant/1.0'
        })
    
    def is_available(self) -> bool:
        """Check if Ollama server is available."""
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama server not available: {e}")
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        try:
            response = self.session.get(f"{self.host}/api/tags")
            response.raise_for_status()
            return response.json().get('models', [])
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            logger.info(f"Pulling model: {model_name}")
            response = self.session.post(
                f"{self.host}/api/pull",
                json={"name": model_name},
                stream=True,
                timeout=300
            )
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if 'status' in data:
                        logger.debug(f"Pull status: {data['status']}")
                    if data.get('error'):
                        logger.error(f"Pull error: {data['error']}")
                        return False
            
            logger.info(f"Successfully pulled model: {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[List[str]] = None,
        system: Optional[str] = None,
        temperature: float = None,
        max_tokens: int = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        """Generate response from model."""
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": {}
            }
            
            if system:
                payload["system"] = system
            
            if images:
                payload["images"] = images
            
            if temperature is not None:
                payload["options"]["temperature"] = temperature
            
            if max_tokens is not None:
                payload["options"]["num_predict"] = max_tokens
            
            response = self.session.post(
                f"{self.host}/api/generate",
                json=payload,
                stream=stream,
                timeout=120
            )
            response.raise_for_status()
            
            if stream:
                return self._stream_response(response)
            else:
                return response.json()
                
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise
    
    def _stream_response(self, response) -> AsyncGenerator:
        """Stream response from Ollama."""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    yield data
                except json.JSONDecodeError:
                    continue
    
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], AsyncGenerator]:
        """Chat with model using conversation format."""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": stream,
                "options": {}
            }
            
            if temperature is not None:
                payload["options"]["temperature"] = temperature
            
            if max_tokens is not None:
                payload["options"]["num_predict"] = max_tokens
            
            response = self.session.post(
                f"{self.host}/api/chat",
                json=payload,
                stream=stream,
                timeout=120
            )
            response.raise_for_status()
            
            if stream:
                return self._stream_response(response)
            else:
                return response.json()
                
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise


class AIEngine:
    """Main AI engine for Jarvis."""
    
    def __init__(self):
        self.ollama = OllamaClient()
        self.conversation_history = []
        self.current_session_id = None
        self.system_prompt = self._build_system_prompt()
        
        # Initialize models
        self._ensure_models_available()
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for the AI assistant."""
        online_status = "online" if config.is_online_mode() else "offline"
        
        return f"""You are Jarvis, a helpful AI assistant running locally on the user's computer.

Current Status:
- Mode: {online_status}
- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- System: Windows 11

Capabilities:
- File management (list, move, rename, analyze files)
- Screen capture and image analysis
- Web search (when in online mode)
- Voice and text interaction
- Task automation

Guidelines:
1. Be helpful, concise, and accurate
2. Respect user privacy and security
3. Use available tools to accomplish tasks
4. Explain what you're doing and why
5. Ask for clarification when needed
6. Perform requested actions directly when they are safe

Available Actions:
- file_list: List files in a directory
- file_move: Move or rename files
- file_analyze: Analyze file contents
- screen_capture: Take a screenshot
- image_analyze: Analyze images
- web_search: Search the web (online mode only)
- system_info: Get system information

Remember: You are running locally and privately on the user's system."""
    
    def _ensure_models_available(self) -> None:
        """Ensure required models are available."""
        if not self.ollama.is_available():
            logger.error("Ollama server is not available")
            return
        
        available_models = [m['name'] for m in self.ollama.list_models()]
        required_models = [
            config.models.text_model,
            config.models.vision_model
        ]
        
        for model in required_models:
            if model not in available_models:
                logger.warning(f"Model {model} not found, attempting to pull...")
                if not self.ollama.pull_model(model):
                    logger.error(f"Failed to pull model {model}")
    
    def start_session(self, session_id: str = None) -> str:
        """Start a new conversation session."""
        if session_id is None:
            session_id = f"session_{int(time.time())}"
        
        self.current_session_id = session_id
        self.conversation_history = []
        
        logger.info(f"Started new session: {session_id}")
        return session_id
    
    def end_session(self) -> None:
        """End current conversation session."""
        if self.current_session_id:
            logger.info(f"Ended session: {self.current_session_id}")
            self.current_session_id = None
            self.conversation_history = []
    
    def process_text_input(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process text input and generate response."""
        start_time = time.time()
        
        try:
            with log_performance(logger, "Text processing"):
                # Add user message to history
                self.conversation_history.append({
                    "role": "user",
                    "content": user_input
                })
                
                # Prepare messages for chat
                messages = [{"role": "system", "content": self.system_prompt}]
                messages.extend(self.conversation_history[-10:])  # Keep last 10 messages
                
                # Generate response
                response = self.ollama.chat(
                    model=config.models.text_model,
                    messages=messages,
                    temperature=config.models.temperature,
                    max_tokens=config.models.max_tokens
                )
                
                ai_response = response['message']['content']
                
                # Add AI response to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": ai_response
                })
                
                processing_time = int((time.time() - start_time) * 1000)
                
                return {
                    "response": ai_response,
                    "processing_time_ms": processing_time,
                    "model_used": config.models.text_model,
                    "tokens_used": response.get('eval_count', 0),
                    "session_id": self.current_session_id
                }
                
        except Exception as e:
            logger.error(f"Error processing text input: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "session_id": self.current_session_id
            }
    
    def process_image_input(
        self,
        image_path: str,
        prompt: str = "Describe this image in detail."
    ) -> Dict[str, Any]:
        """Process image input with vision model."""
        start_time = time.time()
        
        try:
            with log_performance(logger, "Image processing"):
                # Load and encode image
                image_data = self._encode_image(image_path)
                
                # Generate response using vision model
                response = self.ollama.generate(
                    model=config.models.vision_model,
                    prompt=prompt,
                    images=[image_data],
                    temperature=config.models.temperature,
                    max_tokens=config.models.max_tokens
                )
                
                ai_response = response['response']
                processing_time = int((time.time() - start_time) * 1000)
                
                return {
                    "response": ai_response,
                    "processing_time_ms": processing_time,
                    "model_used": config.models.vision_model,
                    "tokens_used": response.get('eval_count', 0),
                    "session_id": self.current_session_id
                }
                
        except Exception as e:
            logger.error(f"Error processing image input: {e}")
            return {
                "response": "I apologize, but I encountered an error analyzing the image. Please try again.",
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "session_id": self.current_session_id
            }
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for Ollama with optimized preprocessing for screen analysis."""
        try:
            with Image.open(image_path) as img:
                logger.info(f"Original image size: {img.size}, mode: {img.mode}")
                
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                    logger.debug("Converted image to RGB mode")
                
                # Use higher resolution for better screen analysis - increased from 1344
                max_size = 2048  # Higher resolution for better UI element recognition
                if max(img.size) > max_size:
                    # Calculate new size maintaining aspect ratio
                    ratio = min(max_size / img.width, max_size / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    logger.debug(f"Resized image to: {img.size}")
                else:
                    logger.debug(f"Image size {img.size} is within limits, no resizing needed")
                
                # Use PNG format for lossless compression - better for UI elements and text
                buffer = io.BytesIO()
                img.save(buffer, format='PNG', optimize=True)
                image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                logger.info(f"Encoded image size: {len(image_data)} characters (PNG format)")
                return image_data
                
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            raise
    
    def get_conversation_context(self, limit: int = 5) -> List[Dict[str, str]]:
        """Get recent conversation context."""
        return self.conversation_history[-limit:] if self.conversation_history else []
    
    def clear_conversation_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get status of AI models."""
        try:
            available_models = self.ollama.list_models()
            
            return {
                "ollama_available": self.ollama.is_available(),
                "available_models": [m['name'] for m in available_models],
                "configured_text_model": config.models.text_model,
                "configured_vision_model": config.models.vision_model,
                "models_ready": all([
                    any(m['name'] == config.models.text_model for m in available_models),
                    any(m['name'] == config.models.vision_model for m in available_models)
                ])
            }
        except Exception as e:
            logger.error(f"Error getting model status: {e}")
            return {
                "ollama_available": False,
                "error": str(e)
            }
    
    def update_system_prompt(self, additional_context: str = None) -> None:
        """Update system prompt with additional context."""
        base_prompt = self._build_system_prompt()
        
        if additional_context:
            self.system_prompt = f"{base_prompt}\n\nAdditional Context:\n{additional_context}"
        else:
            self.system_prompt = base_prompt
        
        logger.debug("System prompt updated")


# Global AI engine instance
ai_engine = AIEngine()
