"""
Main entry point for Jarvis AI Assistant with PyQt6 GUI.
"""

import sys
import signal
import asyncio
from pathlib import Path
from typing import Optional
import uuid

from .core.config import config
from .core.logging import setup_logging, get_logger
from .core.ai_engine import ai_engine
from .input.voice_handler import VoiceHandler
from .input.text_handler import TextHandler
from .output.tts_engine import TTSEngine
from .output.ui_manager_pyqt import UIManager
from .tools.action_dispatcher import ActionDispatcher

logger = get_logger("main_pyqt")


class JarvisAssistant:
    """Main Jarvis AI Assistant application with PyQt6 GUI."""
    
    def __init__(self):
        self.running = False
        self.session_id = None
        
        # Initialize components
        self.voice_handler = None
        self.text_handler = None
        self.tts_engine = None
        self.ui_manager = None
        self.action_dispatcher = None
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()
    
    async def initialize(self) -> bool:
        """Initialize all components."""
        try:
            logger.info("Initializing Jarvis AI Assistant with PyQt6...")
            
            # Validate configuration
            if not config.validate_config():
                logger.error("Configuration validation failed")
                return False
            
            # Check AI engine status
            model_status = ai_engine.get_model_status()
            if not model_status.get('ollama_available'):
                logger.error("Ollama server is not available. Please start Ollama first.")
                return False
            
            if not model_status.get('models_ready'):
                logger.warning("Some models are not available. Functionality may be limited.")
            
            # Initialize components
            if config.voice.enabled:
                self.voice_handler = VoiceHandler()
            else:
                logger.info("Voice features disabled in configuration")
                self.voice_handler = None
            
            self.text_handler = TextHandler()
            self.tts_engine = TTSEngine()
            self.ui_manager = UIManager()
            self.action_dispatcher = ActionDispatcher()
            
            # Initialize UI manager first (PyQt6 needs to be in main thread)
            if not await self.ui_manager.initialize():
                logger.error("Failed to initialize UI manager")
                return False
            
            # Start session
            self.session_id = ai_engine.start_session()
            
            logger.info("Jarvis AI Assistant initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Jarvis: {e}")
            return False
    
    async def start(self) -> None:
        """Start the assistant."""
        if not await self.initialize():
            logger.error("Failed to initialize, exiting")
            sys.exit(1)
        
        self.running = True
        logger.info("Jarvis AI Assistant started")
        
        # Set up UI callbacks
        self.ui_manager.set_message_callback(self._process_user_input)
        self.ui_manager.set_shutdown_callback(self.shutdown)
        
        # Show startup notification
        if config.ui.startup_notification:
            self.ui_manager.show_notification(
                "Jarvis AI Assistant",
                "Assistant is now running and ready to help!"
            )
        
        # Show chat window automatically
        self.ui_manager.show_chat_window()
        
        try:
            # Start background tasks
            tasks = []
            
            # Voice processing task (if enabled)
            if self.voice_handler:
                tasks.append(asyncio.create_task(self._voice_processing_loop()))
            
            # Text input monitoring task
            if self.text_handler:
                tasks.append(asyncio.create_task(self._text_input_loop()))
            
            # UI management task (PyQt6 event processing)
            tasks.append(asyncio.create_task(self._ui_management_loop()))
            
            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.shutdown()
    
    async def _voice_processing_loop(self) -> None:
        """Main voice processing loop."""
        if not self.voice_handler:
            logger.info("Voice processing disabled")
            return
            
        logger.info("Starting voice processing loop")
        
        try:
            if not await self.voice_handler.initialize():
                logger.error("Failed to initialize voice handler")
                return
            
            while self.running:
                try:
                    # Listen for wake word
                    if await self.voice_handler.listen_for_wake_word():
                        logger.info("Wake word detected")
                        
                        # Record user speech
                        audio_data = await self.voice_handler.record_speech()
                        if audio_data:
                            # Convert speech to text
                            text = await self.voice_handler.speech_to_text(audio_data)
                            if text:
                                logger.info(f"User said: {text}")
                                await self._process_user_input(text, "voice")
                
                except Exception as e:
                    logger.error(f"Error in voice processing: {e}")
                    await asyncio.sleep(1)  # Brief pause before retrying
                    
        except Exception as e:
            logger.error(f"Voice processing loop failed: {e}")
    
    async def _text_input_loop(self) -> None:
        """Text input monitoring loop."""
        logger.info("Starting text input monitoring")
        
        try:
            await self.text_handler.initialize()
            
            while self.running:
                try:
                    # Check for hotkey activation
                    text_input = await self.text_handler.wait_for_input()
                    if text_input:
                        logger.info(f"Text input received: {text_input}")
                        await self._process_user_input(text_input, "text")
                
                except Exception as e:
                    logger.error(f"Error in text input processing: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Text input loop failed: {e}")
    
    async def _ui_management_loop(self) -> None:
        """UI management loop for PyQt6."""
        logger.info("Starting UI management")
        
        try:
            while self.running:
                try:
                    # Process PyQt6 events
                    await self.ui_manager.process_events()
                    await asyncio.sleep(0.01)  # Small delay for smooth UI
                
                except Exception as e:
                    logger.error(f"Error in UI management: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"UI management loop failed: {e}")
    
    async def _process_user_input(self, user_input: str, input_type: str) -> None:
        """Process user input and generate response."""
        try:
            logger.info(f"Processing {input_type} input: {user_input}")
            
            # Check for special commands
            if await self._handle_special_commands(user_input):
                return
            
            # Check if input requires action
            action_result = await self.action_dispatcher.process_input(user_input)
            
            if action_result.get('action_taken'):
                # Action was performed, format and return the result directly
                if action_result.get('success'):
                    response = self._format_action_response(action_result, user_input)
                else:
                    # Handle specific error types
                    error_msg = action_result.get('error', 'Unknown error')
                    
                    # Check if it's a confirmation requirement
                    if "requires confirmation" in error_msg.lower():
                        # For delete operations, provide clear confirmation prompt
                        if "delete" in action_result.get('action_taken', '').lower():
                            response = f"⚠️ **Confirmation Required**\n\nAre you sure you want to delete this item? This action cannot be undone (though a backup will be created).\n\nTo confirm, please say: **'delete [filename] confirm'**"
                        else:
                            response = f"This operation requires confirmation. Please add 'confirm' to your request to proceed."
                    else:
                        # Other errors - provide helpful response without passing to AI
                        response = f"I couldn't complete that action: {error_msg}"
            else:
                # No action needed, process as regular conversation
                ai_result = ai_engine.process_text_input(user_input)
                response = ai_result['response']
            
            # Speak response if enabled
            if config.output.speak_responses and self.tts_engine:
                try:
                    await self.tts_engine.speak(response)
                except Exception as e:
                    logger.warning(f"TTS engine not initialized: {e}")
            
            # Show response in UI
            if self.ui_manager:
                self.ui_manager.show_response(user_input, response)
            
            # Log processing time if available
            if action_result.get('action_taken') and action_result.get('success'):
                logger.info(f"Action '{action_result['action_taken']}' completed successfully")
            elif 'ai_result' in locals():
                logger.info(f"Response generated in {ai_result.get('processing_time_ms', 0)}ms")
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            error_response = "I apologize, but I encountered an error processing your request."
            
            if config.output.speak_responses and self.tts_engine:
                try:
                    await self.tts_engine.speak(error_response)
                except Exception as e:
                    logger.warning(f"TTS error: {e}")
            
            if self.ui_manager:
                self.ui_manager.show_response(user_input, error_response)
    
    async def _handle_special_commands(self, user_input: str) -> bool:
        """Handle special system commands."""
        input_lower = user_input.lower().strip()
        
        # Online/offline mode toggle
        if "enable online mode" in input_lower or "go online" in input_lower:
            config.toggle_online_mode()
            response = f"Online mode {'enabled' if config.is_online_mode() else 'disabled'}"
            if self.tts_engine:
                try:
                    await self.tts_engine.speak(response)
                except Exception as e:
                    logger.warning(f"TTS error: {e}")
            if self.ui_manager:
                self.ui_manager.show_response(user_input, response)
            return True
        
        if "disable online mode" in input_lower or "go offline" in input_lower:
            if config.is_online_mode():
                config.toggle_online_mode()
            response = "Offline mode enabled"
            if self.tts_engine:
                try:
                    await self.tts_engine.speak(response)
                except Exception as e:
                    logger.warning(f"TTS error: {e}")
            if self.ui_manager:
                self.ui_manager.show_response(user_input, response)
            return True
        
        # System commands
        if input_lower in ["exit", "quit", "shutdown", "stop"]:
            response = "Shutting down Jarvis. Goodbye!"
            if self.tts_engine:
                try:
                    await self.tts_engine.speak(response)
                except Exception as e:
                    logger.warning(f"TTS error: {e}")
            if self.ui_manager:
                self.ui_manager.show_response(user_input, response)
            self.shutdown()
            return True
        
        if "clear history" in input_lower or "reset conversation" in input_lower:
            ai_engine.clear_conversation_history()
            response = "Conversation history cleared"
            if self.tts_engine:
                try:
                    await self.tts_engine.speak(response)
                except Exception as e:
                    logger.warning(f"TTS error: {e}")
            if self.ui_manager:
                self.ui_manager.show_response(user_input, response)
            return True
        
        return False
    
    def _format_action_response(self, action_result: dict, user_input: str) -> str:
        """Format action result into a user-friendly response."""
        action_type = action_result.get('action_taken', 'unknown')
        result_data = action_result.get('result', {})
        
        if action_type == 'list_files':
            return self._format_file_list_response(result_data, user_input)
        elif action_type == 'analyze_screenshot':
            return self._format_screenshot_analysis_response(result_data)
        elif action_type == 'move_file':
            return self._format_file_move_response(result_data)
        elif action_type == 'analyze_file':
            return self._format_file_analysis_response(result_data)
        elif action_type == 'web_search':
            return self._format_web_search_response(result_data)
        elif action_type == 'system_info':
            return self._format_system_info_response(result_data)
        else:
            return f"Action '{action_type}' completed successfully."
    
    def _format_file_list_response(self, result_data: dict, user_input: str) -> str:
        """Format file listing response."""
        if not result_data.get('success'):
            return f"I couldn't list the files: {result_data.get('error', 'Unknown error')}"
        
        directory = result_data.get('directory', 'the directory')
        files = result_data.get('files', [])
        directories = result_data.get('directories', [])
        
        response = f"Here are the contents of {directory}:\n\n"
        
        if directories:
            response += "**Folders:**\n"
            for folder in directories:
                response += f"📁 {folder['name']}\n"
            response += "\n"
        
        if files:
            response += "**Files:**\n"
            for file in files:
                size = self._format_file_size(file.get('size', 0))
                response += f"📄 {file['name']} ({size})\n"
        
        if not files and not directories:
            response += "The directory is empty."
        else:
            response += f"\nTotal: {len(directories)} folders, {len(files)} files"
        
        return response
    
    def _format_screenshot_analysis_response(self, result_data: dict) -> str:
        """Format screenshot analysis response."""
        if not result_data.get('success'):
            return f"I couldn't analyze the screenshot: {result_data.get('error', 'Unknown error')}"
        
        analysis = result_data.get('analysis', 'No analysis available')
        processing_time = result_data.get('processing_time_ms', 0)
        model_used = result_data.get('model_used', 'unknown')
        
        response = f"Here's what I can see on your screen:\n\n{analysis}"
        
        if processing_time > 0:
            response += f"\n\n*Analysis completed in {processing_time}ms using {model_used}*"
        
        return response
    
    def _format_file_move_response(self, result_data: dict) -> str:
        """Format file move response."""
        if not result_data.get('success'):
            return f"I couldn't move the file: {result_data.get('error', 'Unknown error')}"
        
        source = result_data.get('source', 'the file')
        destination = result_data.get('destination', 'the destination')
        
        return f"Successfully moved {source} to {destination}"
    
    def _format_file_analysis_response(self, result_data: dict) -> str:
        """Format file analysis response."""
        if not result_data.get('success'):
            return f"I couldn't analyze the file: {result_data.get('error', 'Unknown error')}"
        
        name = result_data.get('name', 'Unknown')
        size = self._format_file_size(result_data.get('size', 0))
        extension = result_data.get('extension', '')
        
        response = f"**File Analysis: {name}**\n\n"
        response += f"📄 **Size:** {size}\n"
        response += f"🏷️ **Type:** {extension.upper() if extension else 'Unknown'}\n"
        
        if result_data.get('content_preview'):
            response += f"\n**Content Preview:**\n```\n{result_data['content_preview'][:200]}...\n```"
        
        return response
    
    def _format_web_search_response(self, result_data: dict) -> str:
        """Format web search response."""
        if not result_data.get('success'):
            return f"I couldn't search the web: {result_data.get('error', 'Unknown error')}"
        
        query = result_data.get('query', 'your search')
        abstract = result_data.get('abstract', '')
        answer = result_data.get('answer', '')
        
        response = f"**Search Results for: {query}**\n\n"
        
        if answer:
            response += f"**Quick Answer:** {answer}\n\n"
        
        if abstract:
            response += f"**Summary:** {abstract}\n\n"
        
        related_topics = result_data.get('related_topics', [])
        if related_topics:
            response += "**Related Topics:**\n"
            for topic in related_topics[:3]:  # Show top 3
                response += f"• {topic.get('text', 'No description')}\n"
        
        return response
    
    def _format_system_info_response(self, result_data: dict) -> str:
        """Format system info response."""
        if not result_data.get('success'):
            return f"I couldn't get system information: {result_data.get('error', 'Unknown error')}"
        
        cpu = result_data.get('cpu', {})
        memory = result_data.get('memory', {})
        disk = result_data.get('disk', {})
        
        response = "**System Information:**\n\n"
        response += f"🖥️ **CPU Usage:** {cpu.get('usage_percent', 0):.1f}%\n"
        response += f"💾 **Memory:** {memory.get('used_gb', 0):.1f}GB / {memory.get('total_gb', 0):.1f}GB ({memory.get('percent', 0):.1f}%)\n"
        response += f"💿 **Disk:** {disk.get('used_gb', 0):.1f}GB / {disk.get('total_gb', 0):.1f}GB ({disk.get('percent', 0):.1f}%)\n"
        
        return response
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def shutdown(self) -> None:
        """Shutdown the assistant."""
        if not self.running:
            return
        
        logger.info("Shutting down Jarvis AI Assistant...")
        self.running = False
        
        try:
            # End AI session
            if self.session_id:
                ai_engine.end_session()
            
            # Cleanup components
            if self.voice_handler:
                self.voice_handler.cleanup()
            
            if self.text_handler:
                self.text_handler.cleanup()
            
            if self.tts_engine:
                self.tts_engine.cleanup()
            
            if self.ui_manager:
                self.ui_manager.cleanup()
            
            logger.info("Jarvis AI Assistant shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point."""
    # Setup logging
    app_logger, conversation_logger = setup_logging()
    
    try:
        # Create and start assistant
        assistant = JarvisAssistant()
        await assistant.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


def cli_main():
    """CLI entry point for setup.py."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
