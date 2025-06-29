#!/usr/bin/env python3
"""
Test script for chat GUI functionality.
"""

import sys
import asyncio
import tkinter as tk
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.jarvis.output.ui_manager import UIManager, ChatWindow
from src.jarvis.core.config import config
from src.jarvis.core.logging import setup_logging, get_logger

logger = get_logger("test_chat")

def test_chat_window():
    """Test chat window directly."""
    print("Testing chat window...")
    
    def on_message(message):
        print(f"Received message: {message}")
        # Simulate response
        chat.add_message("Jarvis", f"You said: {message}")
    
    try:
        # Create chat window
        chat = ChatWindow()
        chat.create_window(on_message)
        
        # Add test messages
        chat.add_message("System", "Chat window test started")
        chat.add_message("You", "Hello Jarvis")
        chat.add_message("Jarvis", "Hello! I'm working correctly.")
        
        print("Chat window created successfully!")
        print("Type messages in the chat window to test...")
        
        # Run GUI
        if chat.root:
            chat.root.mainloop()
        
    except Exception as e:
        print(f"Error testing chat window: {e}")
        import traceback
        traceback.print_exc()

async def test_ui_manager():
    """Test UI manager."""
    print("Testing UI manager...")
    
    try:
        # Setup logging
        setup_logging()
        
        # Create UI manager
        ui = UIManager()
        
        # Initialize
        if await ui.initialize():
            print("UI manager initialized successfully")
            
            # Show chat window
            ui.show_chat_window()
            print("Chat window shown")
            
            # Test message callback
            def test_callback(message, input_type):
                print(f"Callback received: {message} ({input_type})")
                # Simulate response
                ui.show_response(message, f"Test response to: {message}")
            
            ui.set_message_callback(test_callback)
            
            # Add test messages
            ui.show_response("Test input", "Test response from UI manager")
            
            print("UI manager test complete - check the chat window")
            
            # Keep running for a bit
            for i in range(100):
                await ui.process_events()
                await asyncio.sleep(0.1)
            
            ui.cleanup()
        else:
            print("Failed to initialize UI manager")
            
    except Exception as e:
        print(f"Error testing UI manager: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function."""
    print("=== Chat GUI Test ===")
    print("1. Testing chat window directly")
    print("2. Testing UI manager")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        test_chat_window()
    elif choice == "2":
        asyncio.run(test_ui_manager())
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
