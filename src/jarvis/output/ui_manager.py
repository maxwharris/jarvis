"""
Fixed UI Manager for Jarvis AI Assistant.
Handles chat window with proper threading and message display.
"""

import asyncio
import threading
from typing import Optional, Dict, Any, Callable
import tkinter as tk
from tkinter import ttk, scrolledtext
import queue
import time
from datetime import datetime
from pathlib import Path

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

from ..core.config import config
from ..core.logging import get_logger

logger = get_logger("ui_manager")


class ChatWindow:
    """Simple, reliable chat interface window."""
    
    def __init__(self):
        self.root = None
        self.chat_display = None
        self.input_entry = None
        self.send_callback = None
        self.is_open = False
        self.message_queue = queue.Queue()
    
    def create_window(self, send_callback: Optional[Callable] = None) -> None:
        """Create chat window in main thread."""
        try:
            if self.is_open and self.root:
                self.root.lift()
                self.root.focus_force()
                return
            
            self.send_callback = send_callback
            
            # Create main window
            self.root = tk.Tk()
            self.root.title("Jarvis AI Assistant - Chat")
            self.root.geometry("700x500")
            self.root.minsize(500, 400)
            
            # Configure style
            if config.ui.theme == "dark":
                self.root.configure(bg="#2b2b2b")
            
            # Create main frame
            main_frame = ttk.Frame(self.root, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Chat display area
            chat_frame = ttk.Frame(main_frame)
            chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # Chat display with scrollbar
            self.chat_display = scrolledtext.ScrolledText(
                chat_frame,
                wrap=tk.WORD,
                state=tk.DISABLED,
                font=("Consolas", 10),
                height=20,
                bg="white",
                fg="black"
            )
            self.chat_display.pack(fill=tk.BOTH, expand=True)
            
            # Input frame
            input_frame = ttk.Frame(main_frame)
            input_frame.pack(fill=tk.X)
            
            # Input entry
            self.input_entry = ttk.Entry(
                input_frame,
                font=("Consolas", 10)
            )
            self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            
            # Send button
            send_button = ttk.Button(
                input_frame,
                text="Send",
                command=self._on_send
            )
            send_button.pack(side=tk.RIGHT)
            
            # Status label
            self.status_label = ttk.Label(main_frame, text="Ready")
            self.status_label.pack(fill=tk.X, pady=(5, 0))
            
            # Bind events
            self.input_entry.bind("<Return>", lambda e: self._on_send())
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            
            # Focus input
            self.input_entry.focus_set()
            
            # Start message processing
            self._process_message_queue()
            
            self.is_open = True
            
            # Add welcome message
            self.add_message("System", "Jarvis AI Assistant ready! Type your message below.")
            
            logger.info("Chat window created successfully")
            
        except Exception as e:
            logger.error(f"Error creating chat window: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_send(self) -> None:
        """Handle send button."""
        try:
            text = self.input_entry.get().strip()
            if text:
                # Add user message immediately
                self.add_message("You", text)
                
                # Clear input
                self.input_entry.delete(0, tk.END)
                
                # Update status
                self.status_label.config(text="Processing...")
                
                # Call callback in separate thread to avoid blocking GUI
                if self.send_callback:
                    def send_async():
                        try:
                            self.send_callback(text)
                        except Exception as e:
                            logger.error(f"Error in send callback: {e}")
                            self.add_message("System", f"Error: {e}")
                        finally:
                            # Reset status (thread-safe)
                            if self.root and self.is_open:
                                try:
                                    self.root.after_idle(lambda: self.status_label.config(text="Ready") if hasattr(self, 'status_label') else None)
                                except RuntimeError:
                                    # GUI thread not available, skip status update
                                    pass
                    
                    thread = threading.Thread(target=send_async, daemon=True)
                    thread.start()
                
        except Exception as e:
            logger.error(f"Error in send handler: {e}")
            self.add_message("System", f"Send error: {e}")
    
    def _on_close(self) -> None:
        """Handle window close."""
        try:
            self.is_open = False
            if self.root:
                self.root.quit()
                self.root.destroy()
                self.root = None
            logger.info("Chat window closed")
        except Exception as e:
            logger.error(f"Error closing chat window: {e}")
    
    def add_message(self, sender: str, message: str) -> None:
        """Add message to chat display (thread-safe)."""
        try:
            # Queue the message for processing
            self.message_queue.put({
                'sender': sender,
                'message': message,
                'timestamp': datetime.now()
            })
        except Exception as e:
            logger.error(f"Error queuing message: {e}")
    
    def _process_message_queue(self) -> None:
        """Process queued messages (runs in GUI thread)."""
        try:
            # Process all queued messages
            while not self.message_queue.empty():
                try:
                    msg_data = self.message_queue.get_nowait()
                    self._add_message_to_display(
                        msg_data['sender'],
                        msg_data['message'],
                        msg_data['timestamp']
                    )
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
            
            # Schedule next check
            if self.root and self.is_open:
                self.root.after(100, self._process_message_queue)
                
        except Exception as e:
            logger.error(f"Error in message queue processing: {e}")
    
    def _add_message_to_display(self, sender: str, message: str, timestamp: datetime) -> None:
        """Add message directly to display (must be called from GUI thread)."""
        try:
            if not self.chat_display:
                return
            
            time_str = timestamp.strftime("%H:%M:%S")
            
            # Enable editing
            self.chat_display.config(state=tk.NORMAL)
            
            # Add message with formatting
            if sender == "System":
                self.chat_display.insert(tk.END, f"[{time_str}] {message}\n", "system")
            elif sender == "You":
                self.chat_display.insert(tk.END, f"[{time_str}] You: {message}\n", "user")
            else:
                self.chat_display.insert(tk.END, f"[{time_str}] {sender}: {message}\n", "assistant")
            
            self.chat_display.insert(tk.END, "\n")
            
            # Disable editing
            self.chat_display.config(state=tk.DISABLED)
            
            # Scroll to bottom
            self.chat_display.see(tk.END)
            
            # Update display
            self.chat_display.update_idletasks()
            
        except Exception as e:
            logger.error(f"Error adding message to display: {e}")
    
    def show(self) -> None:
        """Show chat window."""
        try:
            if self.root and self.is_open:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
        except Exception as e:
            logger.error(f"Error showing chat window: {e}")
    
    def run_mainloop(self) -> None:
        """Run the GUI main loop."""
        try:
            if self.root:
                self.root.mainloop()
        except Exception as e:
            logger.error(f"Error in mainloop: {e}")


class UIManager:
    """Fixed UI manager with proper threading."""
    
    def __init__(self):
        self.chat_window = None
        self.message_callback = None
        self.shutdown_callback = None
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize UI manager."""
        try:
            logger.info("Initializing UI manager...")
            self.initialized = True
            logger.info("UI manager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize UI manager: {e}")
            return False
    
    def show_chat_window(self) -> None:
        """Show chat window."""
        try:
            if not self.chat_window:
                self.chat_window = ChatWindow()
            
            # Create window with callback
            self.chat_window.create_window(self._on_chat_message)
            
            logger.info("Chat window shown")
            
        except Exception as e:
            logger.error(f"Error showing chat window: {e}")
    
    def _on_chat_message(self, message: str) -> None:
        """Handle chat message from user."""
        try:
            logger.info(f"Chat message received: {message}")
            
            if self.message_callback:
                # Call the callback asynchronously
                def call_callback():
                    try:
                        # Create new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.message_callback(message, "text"))
                        loop.close()
                    except Exception as e:
                        logger.error(f"Error in message callback: {e}")
                        # Show error in chat
                        if self.chat_window:
                            self.chat_window.add_message("System", f"Error processing message: {e}")
                
                callback_thread = threading.Thread(target=call_callback, daemon=True)
                callback_thread.start()
            
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
    
    def show_response(self, user_input: str, ai_response: str) -> None:
        """Show conversation in UI."""
        try:
            logger.info(f"Showing response: {ai_response[:50]}...")
            
            # Add to chat window
            if self.chat_window and self.chat_window.is_open:
                self.chat_window.add_message("Jarvis", ai_response)
            
            # Show notification for short responses
            if len(ai_response) < 100 and PLYER_AVAILABLE:
                try:
                    notification.notify(
                        title="Jarvis",
                        message=ai_response[:100],
                        timeout=5,
                        app_name="Jarvis AI Assistant"
                    )
                except Exception as e:
                    logger.error(f"Notification error: {e}")
                    
        except Exception as e:
            logger.error(f"Error showing response: {e}")
    
    def show_notification(self, title: str, message: str, timeout: int = 5) -> None:
        """Show system notification."""
        try:
            if PLYER_AVAILABLE:
                notification.notify(
                    title=title,
                    message=message,
                    timeout=timeout,
                    app_name="Jarvis AI Assistant"
                )
            else:
                logger.info(f"Notification: {title} - {message}")
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
    
    def set_message_callback(self, callback: Callable) -> None:
        """Set callback for handling messages."""
        self.message_callback = callback
    
    def set_shutdown_callback(self, callback: Callable) -> None:
        """Set callback for shutdown requests."""
        self.shutdown_callback = callback
    
    async def process_events(self) -> None:
        """Process UI events."""
        try:
            # Update GUI if chat window exists
            if self.chat_window and self.chat_window.root and self.chat_window.is_open:
                self.chat_window.root.update()
        except Exception as e:
            logger.error(f"Error processing UI events: {e}")
    
    def cleanup(self) -> None:
        """Cleanup UI manager."""
        try:
            logger.info("Cleaning up UI manager...")
            
            if self.chat_window:
                self.chat_window._on_close()
            
            self.initialized = False
            logger.info("UI manager cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during UI cleanup: {e}")


# Test function
def test_fixed_ui():
    """Test the fixed UI."""
    print("Testing fixed UI manager...")
    
    def test_callback(message):
        print(f"Callback received: {message}")
        # Simulate AI response
        import time
        time.sleep(1)  # Simulate processing
        chat.add_message("Jarvis", f"I received your message: '{message}'. This is a test response.")
    
    try:
        chat = ChatWindow()
        chat.create_window(test_callback)
        
        # Add test messages
        chat.add_message("System", "Fixed UI test started")
        chat.add_message("System", "Type messages to test the functionality")
        
        print("Chat window created - test typing messages")
        chat.run_mainloop()
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_fixed_ui()
