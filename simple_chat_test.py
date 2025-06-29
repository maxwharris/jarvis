#!/usr/bin/env python3
"""
Simple chat test to debug GUI issues.
"""

import sys
import tkinter as tk
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_basic_tkinter():
    """Test basic tkinter functionality."""
    print("Testing basic tkinter...")
    
    try:
        root = tk.Tk()
        root.title("Basic Test")
        root.geometry("400x300")
        
        label = tk.Label(root, text="Basic tkinter test - this should work")
        label.pack(pady=20)
        
        def on_click():
            label.config(text="Button clicked!")
            print("Button was clicked")
        
        button = tk.Button(root, text="Click me", command=on_click)
        button.pack(pady=10)
        
        print("Basic tkinter window created - close it to continue")
        root.mainloop()
        print("Basic tkinter test completed")
        
    except Exception as e:
        print(f"Basic tkinter test failed: {e}")
        import traceback
        traceback.print_exc()

def test_chat_window_simple():
    """Test simplified chat window."""
    print("Testing simplified chat window...")
    
    try:
        root = tk.Tk()
        root.title("Simple Chat Test")
        root.geometry("500x400")
        
        # Chat display
        from tkinter import scrolledtext
        chat_display = scrolledtext.ScrolledText(
            root,
            wrap=tk.WORD,
            state=tk.DISABLED,
            height=15
        )
        chat_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Input frame
        input_frame = tk.Frame(root)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        input_entry = tk.Entry(input_frame)
        input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        def add_message(sender, message):
            chat_display.config(state=tk.NORMAL)
            chat_display.insert(tk.END, f"{sender}: {message}\n")
            chat_display.config(state=tk.DISABLED)
            chat_display.see(tk.END)
        
        def on_send():
            text = input_entry.get().strip()
            if text:
                add_message("You", text)
                add_message("Jarvis", f"Echo: {text}")
                input_entry.delete(0, tk.END)
                print(f"Message sent: {text}")
        
        send_button = tk.Button(input_frame, text="Send", command=on_send)
        send_button.pack(side=tk.RIGHT)
        
        input_entry.bind("<Return>", lambda e: on_send())
        
        # Add initial messages
        add_message("System", "Simple chat test started")
        add_message("System", "Type a message and press Enter")
        
        print("Simple chat window created - test typing messages")
        root.mainloop()
        print("Simple chat test completed")
        
    except Exception as e:
        print(f"Simple chat test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main test function."""
    print("=== Simple Chat Test ===")
    print("1. Test basic tkinter")
    print("2. Test simple chat window")
    
    choice = input("Enter choice (1 or 2, or press Enter for 2): ").strip()
    
    if choice == "1":
        test_basic_tkinter()
    else:
        test_chat_window_simple()

if __name__ == "__main__":
    main()
