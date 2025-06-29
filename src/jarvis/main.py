"""
Main entry point for Jarvis AI Assistant.
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
from .output.ui_manager import UIManager
from .tools.action_dispatcher import ActionDispatcher

logger = get_logger("main")


class JarvisAssistant:
    """Main Jarvis AI Assistant application."""
    
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
            logger.info("Initializing Jarvis AI Assistant...")
            
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
        
        # Show startup notification
        if config.ui.startup_notification:
            self.ui_manager.show_notification(
                "Jarvis AI Assistant",
                "Assistant is now running and ready to help!"
            )
        
        # Show chat window automatically (since voice is disabled)
        if not config.voice.enabled:
            self.ui_manager.show_chat_window()
        
        # Set up UI callbacks
        self.ui_manager.set_message_callback(self._process_user_input)
        self.ui_manager.set_shutdown_callback(self.shutdown)
        
        # Start GUI event processing
        if self.ui_manager.chat_window and self.ui_manager.chat_window.root:
            self._setup_gui_integration()
        
        try:
            # Start background tasks
            tasks = []
            
            # Voice processing task
            if self.voice_handler:
                tasks.append(asyncio.create_task(self._voice_processing_loop()))
            
            # Text input monitoring task
            if self.text_handler:
                tasks.append(asyncio.create_task(self._text_input_loop()))
            
            # UI management task
            if self.ui_manager:
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
        """UI management loop."""
        logger.info("Starting UI management")
        
        try:
            await self.ui_manager.initialize()
            
            while self.running:
                try:
                    # Process UI events
                    await self.ui_manager.process_events()
                    await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
                
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
            
            # Check if input requires action - PRIORITY PROCESSING
            action_result = await self.action_dispatcher.process_input(user_input)
            
            if action_result.get('action_taken'):
                # Action was detected and executed
                if action_result.get('success'):
                    # Action succeeded - format direct response
                    response = self._format_action_response(action_result)
                    
                    # Show response immediately without AI processing
                    if self.ui_manager:
                        self.ui_manager.show_response(user_input, response)
                    
                    # Speak response if enabled
                    if config.output.speak_responses and self.tts_engine:
                        await self.tts_engine.speak(response)
                    
                    logger.info(f"Action '{action_result['action_taken']}' completed successfully")
                    return
                else:
                    # Action failed - show error
                    error_msg = f"Action failed: {action_result.get('error', 'Unknown error')}"
                    if self.ui_manager:
                        self.ui_manager.show_response(user_input, error_msg)
                    
                    if config.output.speak_responses and self.tts_engine:
                        await self.tts_engine.speak(error_msg)
                    
                    logger.error(f"Action '{action_result['action_taken']}' failed: {action_result.get('error')}")
                    return
            
            # No action needed, process as regular conversation
            ai_result = ai_engine.process_text_input(user_input)
            response = ai_result['response']
            
            # Speak response if enabled
            if config.output.speak_responses and self.tts_engine:
                await self.tts_engine.speak(response)
            
            # Show response in UI
            if self.ui_manager:
                self.ui_manager.show_response(user_input, response)
            
            logger.info(f"AI response generated in {ai_result.get('processing_time_ms', 0)}ms")
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            error_response = "I apologize, but I encountered an error processing your request."
            
            if self.ui_manager:
                self.ui_manager.show_response(user_input, error_response)
            
            if config.output.speak_responses and self.tts_engine:
                await self.tts_engine.speak(error_response)
    
    def _format_action_response(self, action_result: dict) -> str:
        """Format action result into user-friendly response."""
        try:
            action_type = action_result.get('action_taken', 'unknown')
            result = action_result.get('result', {})
            
            if action_type == 'analyze_screenshot':
                return f"Screenshot Analysis:\n\n{result.get('analysis', 'Analysis completed')}"
            
            elif action_type == 'screenshot':
                path = result.get('path', 'unknown')
                size = result.get('file_size_human', 'unknown size')
                return f"Screenshot captured successfully!\nSaved to: {path}\nFile size: {size}"
            
            elif action_type == 'list_files':
                directory = result.get('directory', 'unknown')
                file_count = result.get('total_files', 0)
                dir_count = result.get('total_directories', 0)
                total_size = result.get('total_size_human', '0 B')
                
                response = f"Directory: {directory}\n"
                response += f"Found {file_count} files and {dir_count} directories\n"
                response += f"Total size: {total_size}\n\n"
                
                # Show first few files
                files = result.get('files', [])[:10]  # Limit to first 10
                if files:
                    response += "Files:\n"
                    for file in files:
                        response += f"  • {file['name']} ({file['size_human']})\n"
                
                # Show first few directories
                dirs = result.get('directories', [])[:5]  # Limit to first 5
                if dirs:
                    response += "\nDirectories:\n"
                    for dir in dirs:
                        response += f"  📁 {dir['name']}\n"
                
                return response
            
            elif action_type == 'copy_file':
                source = result.get('source', 'unknown')
                destination = result.get('destination', 'unknown')
                return f"File copied successfully!\nFrom: {source}\nTo: {destination}"
            
            elif action_type == 'move_file':
                source = result.get('source', 'unknown')
                destination = result.get('destination', 'unknown')
                return f"File moved successfully!\nFrom: {source}\nTo: {destination}"
            
            elif action_type == 'delete_file':
                if result.get('requires_confirmation'):
                    return f"Delete operation requires confirmation.\nFile: {result.get('path')}\nPlease confirm by saying 'delete [filename] confirm'"
                else:
                    path = result.get('path', 'unknown')
                    backup = result.get('backup_location', 'unknown')
                    return f"File deleted successfully!\nDeleted: {path}\nBackup created at: {backup}"
            
            elif action_type == 'analyze_file':
                name = result.get('name', 'unknown')
                size = result.get('size_human', 'unknown')
                file_type = result.get('extension', 'unknown')
                modified = result.get('modified', 'unknown')
                
                response = f"File Analysis: {name}\n"
                response += f"Size: {size}\n"
                response += f"Type: {file_type}\n"
                response += f"Modified: {modified}\n"
                
                if result.get('content_preview'):
                    response += f"\nContent Preview:\n{result['content_preview'][:500]}..."
                
                return response
            
            elif action_type == 'search_files':
                query = result.get('query', 'unknown')
                directory = result.get('directory', 'unknown')
                matches = result.get('matches', [])
                
                response = f"Search Results for '{query}' in {directory}\n"
                response += f"Found {len(matches)} matches\n\n"
                
                for match in matches[:10]:  # Limit to first 10
                    response += f"  • {match['name']} ({match['match_type']} match)\n"
                
                return response
            
            elif action_type == 'temp_info':
                total_size = result.get('total_size_mb', 0)
                folders = result.get('folders', {})
                
                response = f"Temporary Files Info\n"
                response += f"Total size: {total_size} MB\n\n"
                
                for folder, info in folders.items():
                    response += f"{folder}: {info['files']} files ({info['size_mb']} MB)\n"
                
                return response
            
            elif action_type == 'cleanup_temp':
                deleted = result.get('deleted_files', 0)
                size_freed = result.get('size_freed_mb', 0)
                return f"Temp cleanup completed!\nDeleted {deleted} files\nFreed {size_freed} MB of space"
            
            elif action_type == 'system_info':
                cpu = result.get('cpu', {})
                memory = result.get('memory', {})
                disk = result.get('disk', {})
                
                response = f"System Information\n\n"
                response += f"CPU: {cpu.get('usage_percent', 0)}% usage ({cpu.get('count', 0)} cores)\n"
                response += f"Memory: {memory.get('used_gb', 0):.1f}GB / {memory.get('total_gb', 0):.1f}GB ({memory.get('percent', 0)}%)\n"
                response += f"Disk: {disk.get('used_gb', 0):.1f}GB / {disk.get('total_gb', 0):.1f}GB ({disk.get('percent', 0)}%)\n"
                
                return response
            
            elif action_type == 'web_search':
                query = result.get('query', 'unknown')
                abstract = result.get('abstract', '')
                answer = result.get('answer', '')
                
                response = f"Search Results for '{query}'\n\n"
                
                if answer:
                    response += f"Answer: {answer}\n\n"
                
                if abstract:
                    response += f"Summary: {abstract}\n"
                    source = result.get('abstract_source', '')
                    if source:
                        response += f"Source: {source}\n"
                
                topics = result.get('related_topics', [])
                if topics:
                    response += "\nRelated Topics:\n"
                    for topic in topics[:3]:  # Limit to first 3
                        response += f"  • {topic.get('text', '')}\n"
                
                return response
            
            else:
                # Generic response for unknown action types
                return f"Action '{action_type}' completed successfully."
                
        except Exception as e:
            logger.error(f"Error formatting action response: {e}")
            return f"Action completed successfully."
    
    async def _handle_special_commands(self, user_input: str) -> bool:
        """Handle special system commands."""
        input_lower = user_input.lower().strip()
        
        # Online/offline mode toggle
        if "enable online mode" in input_lower or "go online" in input_lower:
            config.toggle_online_mode()
            response = f"Online mode {'enabled' if config.is_online_mode() else 'disabled'}"
            if self.tts_engine:
                await self.tts_engine.speak(response)
            return True
        
        if "disable online mode" in input_lower or "go offline" in input_lower:
            if config.is_online_mode():
                config.toggle_online_mode()
            response = "Offline mode enabled"
            if self.tts_engine:
                await self.tts_engine.speak(response)
            return True
        
        # System commands
        if input_lower in ["exit", "quit", "shutdown", "stop"]:
            response = "Shutting down Jarvis. Goodbye!"
            if self.tts_engine:
                await self.tts_engine.speak(response)
            self.shutdown()
            return True
        
        if "clear history" in input_lower or "reset conversation" in input_lower:
            ai_engine.clear_conversation_history()
            response = "Conversation history cleared"
            if self.tts_engine:
                await self.tts_engine.speak(response)
            return True
        
        return False
    
    def _setup_gui_integration(self) -> None:
        """Setup integration between async loop and GUI."""
        try:
            if self.ui_manager.chat_window and self.ui_manager.chat_window.root:
                # Schedule periodic GUI updates
                def update_gui():
                    try:
                        if self.running and self.ui_manager.chat_window.root:
                            self.ui_manager.chat_window.root.update()
                            # Schedule next update
                            self.ui_manager.chat_window.root.after(100, update_gui)
                    except Exception as e:
                        logger.error(f"Error in GUI update: {e}")
                
                # Start GUI update cycle
                self.ui_manager.chat_window.root.after(100, update_gui)
                logger.info("GUI integration setup complete")
                
        except Exception as e:
            logger.error(f"Error setting up GUI integration: {e}")
    
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
