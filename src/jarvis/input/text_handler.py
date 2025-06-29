"""
Text input handling for Jarvis AI Assistant.
Handles hotkey detection and text input popup.
"""

import asyncio
import threading
from typing import Optional
import tkinter as tk
from tkinter import ttk
import keyboard
import queue
import time

from ..core.config import config
from ..core.logging import get_logger

logger = get_logger("text_handler")


class TextInputPopup:
    """Text input popup window."""
    
    def __init__(self):
        self.root = None
        self.text_var = None
        self.result_queue = queue.Queue()
        self.is_open = False
    
    def create_popup(self) -> None:
        """Create and show the text input popup."""
        try:
            self.root = tk.Tk()
            self.root.title("Jarvis - Text Input")
            self.root.geometry("500x150")
            self.root.resizable(False, False)
            
            # Center the window
            self.root.update_idletasks()
            x = (self.root.winfo_screenwidth() // 2) - (500 // 2)
            y = (self.root.winfo_screenheight() // 2) - (150 // 2)
            self.root.geometry(f"500x150+{x}+{y}")
            
            # Always on top
            self.root.attributes("-topmost", True)
            
            # Configure style
            style = ttk.Style()
            if config.ui.theme == "dark":
                self.root.configure(bg="#2b2b2b")
                style.theme_use("clam")
                style.configure("TLabel", background="#2b2b2b", foreground="white")
                style.configure("TEntry", fieldbackground="#404040", foreground="white")
                style.configure("TButton", background="#404040", foreground="white")
            
            # Create widgets
            main_frame = ttk.Frame(self.root, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Label
            label = ttk.Label(main_frame, text="Enter your message for Jarvis:")
            label.pack(pady=(0, 10))
            
            # Text entry
            self.text_var = tk.StringVar()
            entry = ttk.Entry(
                main_frame, 
                textvariable=self.text_var, 
                font=("Arial", 12),
                width=50
            )
            entry.pack(pady=(0, 10), fill=tk.X)
            entry.focus_set()
            
            # Buttons frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X)
            
            # Send button
            send_button = ttk.Button(
                button_frame, 
                text="Send", 
                command=self._on_send
            )
            send_button.pack(side=tk.RIGHT, padx=(5, 0))
            
            # Cancel button
            cancel_button = ttk.Button(
                button_frame, 
                text="Cancel", 
                command=self._on_cancel
            )
            cancel_button.pack(side=tk.RIGHT)
            
            # Bind events
            entry.bind("<Return>", lambda e: self._on_send())
            entry.bind("<Escape>", lambda e: self._on_cancel())
            self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
            
            # Set timeout
            self.root.after(config.input.popup_timeout * 1000, self._on_timeout)
            
            self.is_open = True
            
        except Exception as e:
            logger.error(f"Error creating text input popup: {e}")
            self._on_cancel()
    
    def _on_send(self) -> None:
        """Handle send button click."""
        try:
            text = self.text_var.get().strip()
            if text:
                self.result_queue.put(text)
            else:
                self.result_queue.put(None)
            self._close_popup()
        except Exception as e:
            logger.error(f"Error in send handler: {e}")
            self._close_popup()
    
    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        try:
            self.result_queue.put(None)
            self._close_popup()
        except Exception as e:
            logger.error(f"Error in cancel handler: {e}")
            self._close_popup()
    
    def _on_timeout(self) -> None:
        """Handle popup timeout."""
        if self.is_open:
            logger.debug("Text input popup timed out")
            self._on_cancel()
    
    def _close_popup(self) -> None:
        """Close the popup window."""
        try:
            self.is_open = False
            if self.root:
                self.root.quit()
                self.root.destroy()
                self.root = None
        except Exception as e:
            logger.error(f"Error closing popup: {e}")
    
    def show_and_wait(self) -> Optional[str]:
        """Show popup and wait for user input."""
        try:
            # Create popup in main thread
            self.create_popup()
            
            # Run the GUI event loop
            if self.root:
                self.root.mainloop()
            
            # Get result
            try:
                result = self.result_queue.get_nowait()
                return result
            except queue.Empty:
                return None
                
        except Exception as e:
            logger.error(f"Error in show_and_wait: {e}")
            return None


class HotkeyManager:
    """Manages global hotkey detection."""
    
    def __init__(self):
        self.hotkey = config.input.hotkey
        self.callback = None
        self.registered = False
        self.stop_event = threading.Event()
    
    def register_hotkey(self, callback) -> bool:
        """Register the global hotkey."""
        try:
            self.callback = callback
            
            # Parse hotkey string
            hotkey_parts = self.hotkey.lower().split('+')
            
            # Register with keyboard library
            keyboard.add_hotkey(self.hotkey, self._on_hotkey_pressed)
            
            self.registered = True
            logger.info(f"Hotkey registered: {self.hotkey}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register hotkey {self.hotkey}: {e}")
            return False
    
    def _on_hotkey_pressed(self) -> None:
        """Handle hotkey press."""
        try:
            if self.callback and not self.stop_event.is_set():
                logger.debug(f"Hotkey pressed: {self.hotkey}")
                self.callback()
        except Exception as e:
            logger.error(f"Error in hotkey callback: {e}")
    
    def unregister_hotkey(self) -> None:
        """Unregister the global hotkey."""
        try:
            if self.registered:
                keyboard.remove_hotkey(self.hotkey)
                self.registered = False
                logger.info(f"Hotkey unregistered: {self.hotkey}")
        except Exception as e:
            logger.error(f"Error unregistering hotkey: {e}")
    
    def stop(self) -> None:
        """Stop hotkey monitoring."""
        self.stop_event.set()
        self.unregister_hotkey()


class TextHandler:
    """Main text input handler."""
    
    def __init__(self):
        self.hotkey_manager = HotkeyManager()
        self.input_queue = queue.Queue()
        self.initialized = False
        self.running = False
    
    async def initialize(self) -> bool:
        """Initialize text input handler."""
        try:
            logger.info("Initializing text input handler...")
            
            # Register hotkey
            if not self.hotkey_manager.register_hotkey(self._on_hotkey_activated):
                logger.error("Failed to register hotkey")
                return False
            
            self.initialized = True
            self.running = True
            
            logger.info("Text input handler initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize text input handler: {e}")
            return False
    
    def _on_hotkey_activated(self) -> None:
        """Handle hotkey activation."""
        try:
            if not self.running:
                return
            
            logger.debug("Text input hotkey activated")
            
            # Run popup in separate thread to avoid blocking
            def show_popup():
                try:
                    popup = TextInputPopup()
                    result = popup.show_and_wait()
                    
                    if result:
                        # Validate input length
                        if len(result) > config.input.max_input_length:
                            logger.warning(f"Input too long: {len(result)} characters")
                            result = result[:config.input.max_input_length]
                        
                        self.input_queue.put(result)
                        logger.debug(f"Text input received: {result}")
                    
                except Exception as e:
                    logger.error(f"Error in popup thread: {e}")
            
            # Start popup thread
            popup_thread = threading.Thread(target=show_popup, daemon=True)
            popup_thread.start()
            
        except Exception as e:
            logger.error(f"Error handling hotkey activation: {e}")
    
    async def wait_for_input(self) -> Optional[str]:
        """Wait for text input from user."""
        if not self.initialized or not self.running:
            return None
        
        try:
            # Check for input with timeout
            while self.running:
                try:
                    # Non-blocking check for input
                    text_input = self.input_queue.get_nowait()
                    return text_input
                except queue.Empty:
                    # No input available, wait a bit
                    await asyncio.sleep(0.1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error waiting for text input: {e}")
            return None
    
    def get_pending_input(self) -> Optional[str]:
        """Get pending input without waiting."""
        try:
            return self.input_queue.get_nowait()
        except queue.Empty:
            return None
    
    def clear_pending_input(self) -> None:
        """Clear any pending input."""
        while not self.input_queue.empty():
            try:
                self.input_queue.get_nowait()
            except queue.Empty:
                break
    
    def cleanup(self) -> None:
        """Cleanup text input handler."""
        logger.info("Cleaning up text input handler...")
        
        self.running = False
        
        # Stop hotkey manager
        if self.hotkey_manager:
            self.hotkey_manager.stop()
        
        # Clear input queue
        self.clear_pending_input()
        
        self.initialized = False
        
        logger.info("Text input handler cleanup complete")


# Test function for standalone testing
def test_text_input():
    """Test function for text input popup."""
    import asyncio
    
    async def test():
        handler = TextHandler()
        
        if await handler.initialize():
            print("Text handler initialized. Press Ctrl+Alt+J to test...")
            
            try:
                while True:
                    text_input = await handler.wait_for_input()
                    if text_input:
                        print(f"Received input: {text_input}")
                        if text_input.lower() in ['quit', 'exit']:
                            break
                    
                    await asyncio.sleep(0.1)
                    
            except KeyboardInterrupt:
                print("Interrupted by user")
            finally:
                handler.cleanup()
        else:
            print("Failed to initialize text handler")
    
    asyncio.run(test())


if __name__ == "__main__":
    test_text_input()
