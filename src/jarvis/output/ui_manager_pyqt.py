"""
Modern PyQt6-based UI Manager for Jarvis AI Assistant.
Features transparent window, modern styling, and proper threading.
"""

import sys
import asyncio
import threading
from typing import Optional, Callable
from datetime import datetime
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTextEdit, QLineEdit, QPushButton, QLabel, QScrollArea,
        QFrame, QSizePolicy, QSystemTrayIcon, QMenu
    )
    from PyQt6.QtCore import (
        Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation,
        QEasingCurve, QRect, QSize
    )
    from PyQt6.QtGui import (
        QFont, QColor, QPalette, QIcon, QPixmap, QPainter,
        QLinearGradient, QBrush, QTextCursor
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

from ..core.config import config
from ..core.logging import get_logger

logger = get_logger("ui_manager_pyqt")


class MessageBubble(QFrame):
    """Custom message bubble widget with modern styling."""
    
    def __init__(self, sender: str, message: str, timestamp: datetime, is_user: bool = False):
        super().__init__()
        self.sender = sender
        self.message = message
        self.timestamp = timestamp
        self.is_user = is_user
        
        self.setup_ui()
        self.apply_styling()
    
    def setup_ui(self):
        """Setup the message bubble UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        # Header with sender and timestamp
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        sender_label = QLabel(self.sender)
        sender_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        
        time_label = QLabel(self.timestamp.strftime("%H:%M:%S"))
        time_label.setFont(QFont("Segoe UI", 8))
        time_label.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        
        header_layout.addWidget(sender_label)
        header_layout.addStretch()
        header_layout.addWidget(time_label)
        
        # Message content
        message_label = QLabel(self.message)
        message_label.setFont(QFont("Segoe UI", 10))
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        layout.addLayout(header_layout)
        layout.addWidget(message_label)
        
        self.setLayout(layout)
    
    def apply_styling(self):
        """Apply modern styling to the message bubble."""
        if self.is_user:
            # User message - right aligned, blue gradient
            self.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #667eea, stop:1 #764ba2);
                    border-radius: 18px;
                    margin: 5px 50px 5px 5px;
                }
                QLabel {
                    color: white;
                    background: transparent;
                }
            """)
        elif self.sender == "System":
            # System message - centered, subtle styling
            self.setStyleSheet("""
                QFrame {
                    background: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 12px;
                    margin: 5px 20px;
                }
                QLabel {
                    color: rgba(255, 255, 255, 0.8);
                    background: transparent;
                }
            """)
        else:
            # AI message - left aligned, dark gradient
            self.setStyleSheet("""
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #2C3E50, stop:1 #34495E);
                    border-radius: 18px;
                    margin: 5px 5px 5px 50px;
                }
                QLabel {
                    color: white;
                    background: transparent;
                }
            """)


class ChatWindow(QMainWindow):
    """Modern chat window with transparency and animations."""
    
    # Signals for thread-safe communication
    message_received = pyqtSignal(str, str, datetime)
    status_changed = pyqtSignal(str)
    
    def __init__(self, ui_manager=None):
        super().__init__()
        self.send_callback = None
        self.ui_manager = ui_manager  # Reference to UIManager for settings
        self.setup_ui()
        self.apply_styling()
        self.setup_signals()
        
        # Animation for new messages
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def setup_ui(self):
        """Setup the main UI components."""
        self.setWindowTitle("Jarvis AI Assistant")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(600, 400)
        
        # Set window flags for modern appearance with resizing capability
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        
        # Enable transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.95)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Title bar
        title_bar = self.create_title_bar()
        main_layout.addWidget(title_bar)
        
        # Chat area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(10)
        self.chat_layout.addStretch()  # Push messages to bottom
        
        self.chat_widget.setLayout(self.chat_layout)
        self.chat_scroll.setWidget(self.chat_widget)
        
        main_layout.addWidget(self.chat_scroll, 1)
        
        # Input area
        input_area = self.create_input_area()
        main_layout.addWidget(input_area)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setFont(QFont("Segoe UI", 9))
        main_layout.addWidget(self.status_label)
        
        central_widget.setLayout(main_layout)
    
    def create_title_bar(self) -> QWidget:
        """Create custom title bar."""
        title_bar = QFrame()
        title_bar.setFixedHeight(40)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 5, 15, 5)
        
        # Title
        title_label = QLabel("Jarvis AI Assistant")
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        
        # Online/Offline toggle button
        self.online_toggle_btn = QPushButton()
        self.online_toggle_btn.setFixedSize(80, 25)
        self.online_toggle_btn.setToolTip("Toggle Online/Offline Mode")
        self.online_toggle_btn.clicked.connect(self.toggle_online_mode)
        self.update_online_button()  # Set initial state
        
        # Settings button
        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(30, 25)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self.open_settings)
        
        # Window controls
        minimize_btn = QPushButton("−")
        minimize_btn.setFixedSize(30, 25)
        minimize_btn.clicked.connect(self.showMinimized)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 25)
        close_btn.clicked.connect(self.close)
        
        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(self.online_toggle_btn)
        layout.addWidget(settings_btn)
        layout.addWidget(minimize_btn)
        layout.addWidget(close_btn)
        
        title_bar.setLayout(layout)
        return title_bar
    
    def create_input_area(self) -> QWidget:
        """Create the input area with text field and send button."""
        input_frame = QFrame()
        input_frame.setFixedHeight(60)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setFont(QFont("Segoe UI", 11))
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.returnPressed.connect(self.send_message)
        
        # Send button
        self.send_button = QPushButton("Send")
        self.send_button.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.send_button.setFixedSize(80, 40)
        self.send_button.clicked.connect(self.send_message)
        
        layout.addWidget(self.input_field)
        layout.addWidget(self.send_button)
        
        input_frame.setLayout(layout)
        return input_frame
    
    def apply_styling(self):
        """Apply modern styling with transparency and gradients."""
        self.setStyleSheet("""
            QMainWindow {
                background: rgba(20, 20, 30, 0.9);
                border-radius: 15px;
            }
            
            QFrame {
                background: rgba(30, 30, 40, 0.8);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            QLabel {
                color: white;
                background: transparent;
            }
            
            QLineEdit {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 20px;
                padding: 10px 15px;
                color: white;
                font-size: 11px;
            }
            
            QLineEdit:focus {
                border: 2px solid #667eea;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border: none;
                border-radius: 20px;
                color: white;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7c8ef0, stop:1 #8a5cb8);
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5a6bd8, stop:1 #6a4a9c);
            }
            
            QScrollArea {
                background: transparent;
                border: none;
            }
            
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 0.1);
                width: 8px;
                border-radius: 4px;
            }
            
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
        """)
    
    def setup_signals(self):
        """Setup signal connections."""
        self.message_received.connect(self.add_message_to_chat)
        self.status_changed.connect(self.update_status)
    
    def set_send_callback(self, callback: Callable):
        """Set the callback for sending messages."""
        self.send_callback = callback
    
    def send_message(self):
        """Handle sending a message."""
        text = self.input_field.text().strip()
        if text and self.send_callback:
            # Add user message immediately
            self.add_message("You", text, datetime.now(), is_user=True)
            
            # Clear input
            self.input_field.clear()
            
            # Update status
            self.status_changed.emit("Processing...")
            
            # Call callback in separate thread
            def send_async():
                try:
                    self.send_callback(text)
                except Exception as e:
                    logger.error(f"Error in send callback: {e}")
                    self.message_received.emit("System", f"Error: {e}", datetime.now())
                finally:
                    self.status_changed.emit("Ready")
            
            thread = threading.Thread(target=send_async, daemon=True)
            thread.start()
    
    def add_message(self, sender: str, message: str, timestamp: datetime, is_user: bool = False):
        """Add message to chat (thread-safe via signal)."""
        self.message_received.emit(sender, message, timestamp)
    
    def add_message_to_chat(self, sender: str, message: str, timestamp: datetime):
        """Add message to chat display (called from signal)."""
        try:
            is_user = (sender == "You")
            
            # Create message bubble
            bubble = MessageBubble(sender, message, timestamp, is_user)
            
            # Insert before the stretch
            self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
            
            # Scroll to bottom
            QTimer.singleShot(100, self.scroll_to_bottom)
            
        except Exception as e:
            logger.error(f"Error adding message to chat: {e}")
    
    def scroll_to_bottom(self):
        """Scroll chat to bottom."""
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def update_status(self, status: str):
        """Update status label."""
        self.status_label.setText(status)
    
    def toggle_online_mode(self):
        """Toggle between online and offline mode."""
        try:
            # Toggle the mode using config
            new_state = config.toggle_online_mode()
            
            # Update button appearance
            self.update_online_button()
            
            # Notify AI engine to refresh system prompt
            try:
                from ..core.ai_engine import ai_engine
                ai_engine.system_prompt = ai_engine._build_system_prompt()
                logger.info("AI engine system prompt updated with new online/offline state")
            except Exception as e:
                logger.error(f"Error updating AI engine system prompt: {e}")
            
            # Show status message
            mode_text = "Online" if new_state else "Offline"
            self.add_message("System", f"Switched to {mode_text} mode", datetime.now())
            
            logger.info(f"Online mode toggled to: {new_state}")
            
        except Exception as e:
            logger.error(f"Error toggling online mode: {e}")
            self.add_message("System", f"Error toggling online mode: {e}", datetime.now())
    
    def update_online_button(self):
        """Update the online/offline button appearance based on current state."""
        try:
            is_online = config.is_online_mode()
            
            if is_online:
                # Online state - green with globe icon
                self.online_toggle_btn.setText("🌐 Online")
                self.online_toggle_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #28a745, stop:1 #20c997);
                        border: none;
                        border-radius: 12px;
                        color: white;
                        font-weight: bold;
                        font-size: 9px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #34ce57, stop:1 #2dd4aa);
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #1e7e34, stop:1 #1a9e7e);
                    }
                """)
            else:
                # Offline state - gray with lock icon
                self.online_toggle_btn.setText("🔒 Offline")
                self.online_toggle_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #6c757d, stop:1 #495057);
                        border: none;
                        border-radius: 12px;
                        color: white;
                        font-weight: bold;
                        font-size: 9px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #7a8288, stop:1 #545b62);
                    }
                    QPushButton:pressed {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #5a6268, stop:1 #3d4449);
                    }
                """)
            
        except Exception as e:
            logger.error(f"Error updating online button: {e}")
    
    def open_settings(self):
        """Open the settings window."""
        try:
            if self.ui_manager:
                # Use UIManager's settings method for proper window management
                self.ui_manager.show_settings()
                logger.info("Settings window opened via UIManager from chat window")
            else:
                # Fallback to standalone function if no UIManager reference
                from ..ui.settings_window import show_settings_window
                settings_window = show_settings_window()
                logger.info("Settings window opened from chat window (fallback)")
        except Exception as e:
            logger.error(f"Error opening settings: {e}")
            self.add_message("System", f"Error opening settings: {e}", datetime.now())
    
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging."""
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()


class UIManager:
    """Modern PyQt6-based UI manager with proper threading."""
    
    def __init__(self):
        self.app = None
        self.chat_window = None
        self.settings_window = None  # Store settings window reference
        self.message_callback = None
        self.shutdown_callback = None
        self.initialized = False
        
        # System tray
        self.tray_icon = None
    
    async def initialize(self) -> bool:
        """Initialize the UI manager."""
        try:
            if not PYQT_AVAILABLE:
                logger.error("PyQt6 is not available. Please install it: pip install PyQt6")
                return False
            
            logger.info("Initializing PyQt6 UI manager...")
            
            # Create QApplication if it doesn't exist
            if not QApplication.instance():
                self.app = QApplication(sys.argv)
                self.app.setApplicationName("Jarvis AI Assistant")
                self.app.setQuitOnLastWindowClosed(False)
            else:
                self.app = QApplication.instance()
            
            # Setup system tray
            self.setup_system_tray()
            
            self.initialized = True
            logger.info("PyQt6 UI manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize PyQt6 UI manager: {e}")
            return False
    
    def setup_system_tray(self):
        """Setup system tray icon."""
        try:
            if QSystemTrayIcon.isSystemTrayAvailable():
                self.tray_icon = QSystemTrayIcon()
                
                # Create a simple icon (you can replace with actual icon file)
                pixmap = QPixmap(16, 16)
                pixmap.fill(QColor(102, 126, 234))  # Blue color
                self.tray_icon.setIcon(QIcon(pixmap))
                
                # Create tray menu
                tray_menu = QMenu()
                
                show_action = tray_menu.addAction("Show Chat")
                show_action.triggered.connect(self.show_chat_window)
                
                settings_action = tray_menu.addAction("Settings")
                settings_action.triggered.connect(self.show_settings)
                
                tray_menu.addSeparator()
                
                quit_action = tray_menu.addAction("Quit")
                quit_action.triggered.connect(self.quit_application)
                
                self.tray_icon.setContextMenu(tray_menu)
                self.tray_icon.show()
                
                # Double-click to show window
                self.tray_icon.activated.connect(self.tray_icon_activated)
                
        except Exception as e:
            logger.error(f"Error setting up system tray: {e}")
    
    def tray_icon_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_chat_window()
    
    def show_chat_window(self):
        """Show the chat window."""
        try:
            if not self.chat_window:
                self.chat_window = ChatWindow(ui_manager=self)  # Pass UIManager reference
                self.chat_window.set_send_callback(self._on_chat_message)
                
                # Add welcome message
                self.chat_window.add_message(
                    "System",
                    "Jarvis AI Assistant ready! Type your message below.",
                    datetime.now()
                )
            
            self.chat_window.show()
            self.chat_window.raise_()
            self.chat_window.activateWindow()
            
            logger.info("Chat window shown")
            
        except Exception as e:
            logger.error(f"Error showing chat window: {e}")
    
    def show_settings(self):
        """Show the settings window."""
        try:
            # Check if settings window already exists and is visible
            if self.settings_window and not self.settings_window.isHidden():
                # Bring existing window to front
                self.settings_window.show()
                self.settings_window.raise_()
                self.settings_window.activateWindow()
                logger.info("Brought existing settings window to front")
                return
            
            # Create new settings window
            from ..ui.settings_window import SettingsWindow
            self.settings_window = SettingsWindow()
            
            # Connect close event to cleanup
            def on_settings_closed():
                self.settings_window = None
                logger.info("Settings window closed")
            
            self.settings_window.destroyed.connect(on_settings_closed)
            
            # Show the window
            self.settings_window.show()
            self.settings_window.raise_()
            self.settings_window.activateWindow()
            
            logger.info("Settings window created and shown")
            
        except Exception as e:
            logger.error(f"Error showing settings window: {e}")
    
    def _on_chat_message(self, message: str):
        """Handle chat message from user."""
        try:
            logger.info(f"Chat message received: {message}")
            
            if self.message_callback:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.message_callback(message, "text"))
                loop.close()
                
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
            if self.chat_window:
                self.chat_window.add_message(
                    "System",
                    f"Error processing message: {e}",
                    datetime.now()
                )
    
    def show_response(self, user_input: str, ai_response: str):
        """Show AI response in the chat."""
        try:
            logger.info(f"Showing response: {ai_response[:50]}...")
            
            if self.chat_window:
                self.chat_window.add_message("Jarvis", ai_response, datetime.now())
            
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
    
    def show_notification(self, title: str, message: str, timeout: int = 5):
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
    
    def set_message_callback(self, callback: Callable):
        """Set callback for handling messages."""
        self.message_callback = callback
    
    def set_shutdown_callback(self, callback: Callable):
        """Set callback for shutdown requests."""
        self.shutdown_callback = callback
    
    async def process_events(self):
        """Process UI events."""
        try:
            if self.app:
                self.app.processEvents()
        except Exception as e:
            logger.error(f"Error processing UI events: {e}")
    
    def quit_application(self):
        """Quit the application."""
        try:
            if self.shutdown_callback:
                self.shutdown_callback()
            
            if self.app:
                self.app.quit()
                
        except Exception as e:
            logger.error(f"Error quitting application: {e}")
    
    def cleanup(self):
        """Cleanup UI manager."""
        try:
            logger.info("Cleaning up PyQt6 UI manager...")
            
            if self.chat_window:
                self.chat_window.close()
            
            if self.tray_icon:
                self.tray_icon.hide()
            
            self.initialized = False
            logger.info("PyQt6 UI manager cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during UI cleanup: {e}")


# Test function
def test_pyqt_ui():
    """Test the PyQt6 UI."""
    if not PYQT_AVAILABLE:
        print("PyQt6 is not available. Please install it: pip install PyQt6")
        return
    
    print("Testing PyQt6 UI manager...")
    
    def test_callback(message):
        print(f"Callback received: {message}")
        # Simulate AI response
        import time
        time.sleep(1)
        ui.show_response(message, f"I received your message: '{message}'. This is a test response from the modern PyQt6 interface!")
    
    try:
        app = QApplication(sys.argv)
        
        ui = UIManager()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if loop.run_until_complete(ui.initialize()):
            ui.set_message_callback(lambda msg, type: test_callback(msg))
            ui.show_chat_window()
            
            print("Modern PyQt6 chat window created - test typing messages")
            app.exec()
        else:
            print("Failed to initialize UI manager")
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_pyqt_ui()
