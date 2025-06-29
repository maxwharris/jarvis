"""
UI Manager for Jarvis AI Assistant.
Handles system tray, notifications, and user interface elements.
"""

import asyncio
import threading
from typing import Optional, Dict, Any, List
import tkinter as tk
from tkinter import ttk, scrolledtext
import queue
import time
from datetime import datetime
from pathlib import Path

try:
    import pystray
    from pystray import MenuItem as item
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    # Create dummy classes for when pystray is not available
    class pystray:
        class Menu:
            SEPARATOR = "---"
            def __init__(self, *args, **kwargs):
                pass
        
        class Icon:
            def __init__(self, *args, **kwargs):
                pass
            def run(self):
                pass
            def stop(self):
                pass
    
    class item:
        def __init__(self, *args, **kwargs):
            pass

try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    # Create dummy classes for when PIL is not available
    class Image:
        @staticmethod
        def new(mode, size, color=(0, 0, 0, 0)):
            return None
    
    class ImageDraw:
        @staticmethod
        def Draw(image):
            return None

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

from ..core.config import config
from ..core.logging import get_logger

logger = get_logger("ui_manager")


class SystemTrayManager:
    """System tray icon and menu management."""
    
    def __init__(self, ui_manager):
        self.ui_manager = ui_manager
        self.icon = None
        self.running = False
    
    def create_icon_image(self) -> Image.Image:
        """Create system tray icon image."""
        try:
            # Create a simple icon
            width = 64
            height = 64
            image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Draw a simple "J" for Jarvis
            draw.ellipse([8, 8, 56, 56], fill=(0, 120, 215, 255))
            draw.text((20, 15), "J", fill=(255, 255, 255, 255))
            
            return image
            
        except Exception as e:
            logger.error(f"Error creating icon image: {e}")
            # Fallback to simple colored square
            image = Image.new('RGBA', (64, 64), (0, 120, 215, 255))
            return image
    
    def create_menu(self) -> pystray.Menu:
        """Create system tray menu."""
        try:
            return pystray.Menu(
                item('Show Chat', self._show_chat_window),
                item('Voice Status', self._toggle_voice),
                item('Online Mode', self._toggle_online_mode, checked=lambda item: config.is_online_mode()),
                pystray.Menu.SEPARATOR,
                item('Settings', self._show_settings),
                item('About', self._show_about),
                pystray.Menu.SEPARATOR,
                item('Exit', self._exit_application)
            )
        except Exception as e:
            logger.error(f"Error creating menu: {e}")
            return pystray.Menu(item('Exit', self._exit_application))
    
    def _show_chat_window(self, icon, item):
        """Show chat window."""
        try:
            self.ui_manager.show_chat_window()
        except Exception as e:
            logger.error(f"Error showing chat window: {e}")
    
    def _toggle_voice(self, icon, item):
        """Toggle voice input."""
        try:
            # This would toggle voice input on/off
            logger.info("Voice toggle requested")
        except Exception as e:
            logger.error(f"Error toggling voice: {e}")
    
    def _toggle_online_mode(self, icon, item):
        """Toggle online mode."""
        try:
            new_state = config.toggle_online_mode()
            mode = "online" if new_state else "offline"
            self.ui_manager.show_notification("Jarvis", f"Switched to {mode} mode")
        except Exception as e:
            logger.error(f"Error toggling online mode: {e}")
    
    def _show_settings(self, icon, item):
        """Show settings window."""
        try:
            self.ui_manager.show_settings_window()
        except Exception as e:
            logger.error(f"Error showing settings: {e}")
    
    def _show_about(self, icon, item):
        """Show about dialog."""
        try:
            self.ui_manager.show_about_dialog()
        except Exception as e:
            logger.error(f"Error showing about dialog: {e}")
    
    def _exit_application(self, icon, item):
        """Exit application."""
        try:
            self.ui_manager.request_shutdown()
        except Exception as e:
            logger.error(f"Error exiting application: {e}")
    
    def start(self) -> bool:
        """Start system tray."""
        if not PYSTRAY_AVAILABLE:
            logger.warning("pystray not available, system tray disabled")
            return False
        
        try:
            image = self.create_icon_image()
            menu = self.create_menu()
            
            self.icon = pystray.Icon(
                "jarvis",
                image,
                "Jarvis AI Assistant",
                menu
            )
            
            # Run in separate thread
            def run_tray():
                try:
                    self.running = True
                    self.icon.run()
                except Exception as e:
                    logger.error(f"Error running system tray: {e}")
                finally:
                    self.running = False
            
            tray_thread = threading.Thread(target=run_tray, daemon=True)
            tray_thread.start()
            
            logger.info("System tray started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start system tray: {e}")
            return False
    
    def stop(self) -> None:
        """Stop system tray."""
        try:
            if self.icon and self.running:
                self.icon.stop()
                self.running = False
                logger.info("System tray stopped")
        except Exception as e:
            logger.error(f"Error stopping system tray: {e}")


class ChatWindow:
    """Chat interface window."""
    
    def __init__(self):
        self.root = None
        self.chat_display = None
        self.input_entry = None
        self.send_callback = None
        self.is_open = False
    
    def create_window(self, send_callback=None) -> None:
        """Create chat window."""
        try:
            if self.is_open:
                if self.root:
                    self.root.lift()
                    self.root.focus_force()
                return
            
            self.send_callback = send_callback
            
            self.root = tk.Tk()
            self.root.title("Jarvis AI Assistant - Chat")
            self.root.geometry("600x500")
            
            # Configure style
            if config.ui.theme == "dark":
                self.root.configure(bg="#2b2b2b")
            
            # Create main frame
            main_frame = ttk.Frame(self.root, padding="10")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Chat display area
            chat_frame = ttk.Frame(main_frame)
            chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            self.chat_display = scrolledtext.ScrolledText(
                chat_frame,
                wrap=tk.WORD,
                state=tk.DISABLED,
                font=("Arial", 10),
                height=20
            )
            self.chat_display.pack(fill=tk.BOTH, expand=True)
            
            # Input frame
            input_frame = ttk.Frame(main_frame)
            input_frame.pack(fill=tk.X)
            
            # Input entry
            self.input_entry = ttk.Entry(
                input_frame,
                font=("Arial", 10)
            )
            self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
            
            # Send button
            send_button = ttk.Button(
                input_frame,
                text="Send",
                command=self._on_send
            )
            send_button.pack(side=tk.RIGHT)
            
            # Bind events
            self.input_entry.bind("<Return>", lambda e: self._on_send())
            self.root.protocol("WM_DELETE_WINDOW", self._on_close)
            
            # Focus input
            self.input_entry.focus_set()
            
            self.is_open = True
            
        except Exception as e:
            logger.error(f"Error creating chat window: {e}")
    
    def _on_send(self) -> None:
        """Handle send button."""
        try:
            text = self.input_entry.get().strip()
            if text and self.send_callback:
                self.send_callback(text)
                self.input_entry.delete(0, tk.END)
        except Exception as e:
            logger.error(f"Error in send handler: {e}")
    
    def _on_close(self) -> None:
        """Handle window close."""
        try:
            self.is_open = False
            if self.root:
                self.root.destroy()
                self.root = None
        except Exception as e:
            logger.error(f"Error closing chat window: {e}")
    
    def add_message(self, sender: str, message: str) -> None:
        """Add message to chat display."""
        try:
            if not self.chat_display:
                return
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: {message}\n\n")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)
            
        except Exception as e:
            logger.error(f"Error adding message to chat: {e}")
    
    def show(self) -> None:
        """Show chat window."""
        try:
            if self.root and self.is_open:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
        except Exception as e:
            logger.error(f"Error showing chat window: {e}")


class NotificationManager:
    """Notification management."""
    
    def __init__(self):
        self.notification_queue = queue.Queue()
    
    def show_notification(self, title: str, message: str, timeout: int = 5) -> bool:
        """Show system notification."""
        try:
            if not config.output.show_notifications:
                return False
            
            if PLYER_AVAILABLE:
                notification.notify(
                    title=title,
                    message=message,
                    timeout=timeout,
                    app_name="Jarvis AI Assistant"
                )
                return True
            else:
                # Fallback to console output
                logger.info(f"Notification: {title} - {message}")
                return False
                
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
            return False


class UIManager:
    """Main UI manager."""
    
    def __init__(self):
        self.system_tray = None
        self.chat_window = None
        self.notification_manager = NotificationManager()
        self.shutdown_callback = None
        self.message_callback = None
        self.initialized = False
        self.event_queue = queue.Queue()
    
    async def initialize(self) -> bool:
        """Initialize UI manager."""
        try:
            logger.info("Initializing UI manager...")
            
            # Initialize notification manager
            self.notification_manager = NotificationManager()
            
            # Initialize system tray if enabled
            if config.ui.system_tray:
                self.system_tray = SystemTrayManager(self)
                if not self.system_tray.start():
                    logger.warning("Failed to start system tray")
            
            # Initialize chat window
            self.chat_window = ChatWindow()
            
            self.initialized = True
            logger.info("UI manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize UI manager: {e}")
            return False
    
    async def process_events(self) -> None:
        """Process UI events."""
        try:
            # Process any queued events
            while not self.event_queue.empty():
                try:
                    event = self.event_queue.get_nowait()
                    await self._handle_event(event)
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"Error processing UI event: {e}")
        except Exception as e:
            logger.error(f"Error in process_events: {e}")
    
    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """Handle UI event."""
        try:
            event_type = event.get('type')
            
            if event_type == 'show_notification':
                self.notification_manager.show_notification(
                    event.get('title', ''),
                    event.get('message', ''),
                    event.get('timeout', 5)
                )
            elif event_type == 'show_chat':
                self.show_chat_window()
            elif event_type == 'add_message':
                if self.chat_window:
                    self.chat_window.add_message(
                        event.get('sender', ''),
                        event.get('message', '')
                    )
            
        except Exception as e:
            logger.error(f"Error handling UI event: {e}")
    
    def show_notification(self, title: str, message: str, timeout: int = 5) -> None:
        """Show notification."""
        try:
            self.event_queue.put({
                'type': 'show_notification',
                'title': title,
                'message': message,
                'timeout': timeout
            })
        except Exception as e:
            logger.error(f"Error queuing notification: {e}")
    
    def show_chat_window(self) -> None:
        """Show chat window."""
        try:
            if not self.chat_window:
                self.chat_window = ChatWindow()
            
            # Create window in main thread (not separate thread)
            self.chat_window.create_window(self._on_chat_message)
            
        except Exception as e:
            logger.error(f"Error showing chat window: {e}")
    
    def _on_chat_message(self, message: str) -> None:
        """Handle chat message from user."""
        try:
            if self.message_callback:
                # Run callback in thread to avoid blocking UI
                def send_message():
                    try:
                        asyncio.run(self.message_callback(message, "text"))
                    except Exception as e:
                        logger.error(f"Error in message callback: {e}")
                
                message_thread = threading.Thread(target=send_message, daemon=True)
                message_thread.start()
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
    
    def show_response(self, user_input: str, ai_response: str) -> None:
        """Show conversation in UI."""
        try:
            # Add to chat window if open (thread-safe)
            if self.chat_window and self.chat_window.is_open and self.chat_window.root:
                # Use tkinter's after() method for thread-safe GUI updates
                self.chat_window.root.after(0, lambda: self._add_messages_to_chat(user_input, ai_response))
            
            # Show notification for responses
            if len(ai_response) < 100:  # Short responses as notifications
                self.show_notification("Jarvis", ai_response[:100])
                
        except Exception as e:
            logger.error(f"Error showing response: {e}")
    
    def _add_messages_to_chat(self, user_input: str, ai_response: str) -> None:
        """Add messages to chat window (called in GUI thread)."""
        try:
            if self.chat_window and self.chat_window.is_open:
                self.chat_window.add_message("You", user_input)
                self.chat_window.add_message("Jarvis", ai_response)
        except Exception as e:
            logger.error(f"Error adding messages to chat: {e}")
    
    def show_settings_window(self) -> None:
        """Show settings window."""
        try:
            # Simple settings dialog
            def create_settings():
                root = tk.Tk()
                root.title("Jarvis Settings")
                root.geometry("400x300")
                
                # Add basic settings here
                ttk.Label(root, text="Settings (Coming Soon)").pack(pady=20)
                ttk.Button(root, text="Close", command=root.destroy).pack(pady=10)
                
                root.mainloop()
            
            settings_thread = threading.Thread(target=create_settings, daemon=True)
            settings_thread.start()
            
        except Exception as e:
            logger.error(f"Error showing settings: {e}")
    
    def show_about_dialog(self) -> None:
        """Show about dialog."""
        try:
            def create_about():
                root = tk.Tk()
                root.title("About Jarvis")
                root.geometry("300x200")
                
                ttk.Label(root, text="Jarvis AI Assistant", font=("Arial", 14, "bold")).pack(pady=10)
                ttk.Label(root, text="Version 1.0.0").pack(pady=5)
                ttk.Label(root, text="Local AI Assistant").pack(pady=5)
                ttk.Button(root, text="Close", command=root.destroy).pack(pady=20)
                
                root.mainloop()
            
            about_thread = threading.Thread(target=create_about, daemon=True)
            about_thread.start()
            
        except Exception as e:
            logger.error(f"Error showing about dialog: {e}")
    
    def set_message_callback(self, callback) -> None:
        """Set callback for handling messages."""
        self.message_callback = callback
    
    def set_shutdown_callback(self, callback) -> None:
        """Set callback for shutdown requests."""
        self.shutdown_callback = callback
    
    def request_shutdown(self) -> None:
        """Request application shutdown."""
        try:
            if self.shutdown_callback:
                self.shutdown_callback()
        except Exception as e:
            logger.error(f"Error requesting shutdown: {e}")
    
    def cleanup(self) -> None:
        """Cleanup UI manager."""
        logger.info("Cleaning up UI manager...")
        
        try:
            # Stop system tray
            if self.system_tray:
                self.system_tray.stop()
            
            # Close chat window
            if self.chat_window:
                self.chat_window._on_close()
            
            self.initialized = False
            logger.info("UI manager cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during UI cleanup: {e}")


# Test function
def test_ui():
    """Test UI components."""
    import asyncio
    
    async def test():
        ui = UIManager()
        
        if await ui.initialize():
            print("UI manager initialized")
            
            # Show test notification
            ui.show_notification("Test", "This is a test notification")
            
            # Keep running for a bit
            for i in range(10):
                await ui.process_events()
                await asyncio.sleep(1)
            
            ui.cleanup()
        else:
            print("Failed to initialize UI manager")
    
    asyncio.run(test())


if __name__ == "__main__":
    test_ui()
