#!/usr/bin/env python3
"""
Thread-free GUI startup for Jarvis AI Assistant.
This version runs the GUI in the main thread to avoid threading issues.
"""

import asyncio
import sys
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import threading
import time

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

class MainThreadGUI:
    """GUI that runs entirely in the main thread."""
    
    def __init__(self):
        self.root = None
        self.startup_complete = False
        self.user_wants_to_continue = False
        self.startup_success = False
        
    def create_window(self):
        """Create the startup window."""
        self.root = tk.Tk()
        self.root.title("Jarvis AI Assistant - Setup")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.root.winfo_screenheight() // 2) - (500 // 2)
        self.root.geometry(f"600x500+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame, 
            text="Jarvis AI Assistant", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Status
        self.status_var = tk.StringVar(value="Initializing...")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=(0, 20))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            variable=self.progress_var, 
            maximum=100,
            length=400
        )
        self.progress_bar.pack(pady=(0, 20))
        
        # Details text area
        details_frame = ttk.LabelFrame(main_frame, text="Setup Details", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        self.details_text = tk.Text(
            details_frame,
            height=15,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        
        scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=scrollbar.set)
        
        self.details_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        self.continue_button = ttk.Button(
            button_frame,
            text="Please wait...",
            command=self._on_continue,
            state=tk.DISABLED
        )
        self.continue_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Exit",
            command=self._on_exit
        ).pack(side=tk.RIGHT)
        
        # Start the setup process
        self.root.after(100, self._start_setup_process)
    
    def _start_setup_process(self):
        """Start the setup process in a background thread."""
        setup_thread = threading.Thread(target=self._run_setup, daemon=True)
        setup_thread.start()
        
        # Start checking for updates
        self._check_setup_progress()
    
    def _run_setup(self):
        """Run the setup process in background thread."""
        try:
            from jarvis.core.startup_manager import StartupManager
            
            # Create startup manager
            startup_manager = StartupManager()
            
            # Run setup without GUI (we are the GUI)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            success = loop.run_until_complete(
                startup_manager.run_startup_process(show_gui=False)
            )
            
            self.startup_success = success
            self.startup_complete = True
            
        except Exception as e:
            self.startup_success = False
            self.startup_complete = True
            self.add_detail(f"Setup failed: {e}", "error")
    
    def _check_setup_progress(self):
        """Check setup progress and update GUI."""
        if not self.startup_complete:
            # Update progress animation
            current = self.progress_var.get()
            if current >= 90:
                self.progress_var.set(10)
            else:
                self.progress_var.set(current + 2)
            
            # Schedule next check
            self.root.after(200, self._check_setup_progress)
        else:
            # Setup is complete
            if self.startup_success:
                self.progress_var.set(100)
                self.status_var.set("Setup complete! Ready to start Jarvis.")
                self.add_detail("✅ Setup completed successfully!", "success")
                self.continue_button.config(text="Start Jarvis", state=tk.NORMAL)
            else:
                self.progress_var.set(0)
                self.status_var.set("Setup failed - please check details above")
                self.add_detail("❌ Setup failed. Please resolve issues and try again.", "error")
                self.continue_button.config(text="Exit", state=tk.NORMAL)
    
    def add_detail(self, message: str, level: str = "info"):
        """Add detail message to text area."""
        self.details_text.config(state=tk.NORMAL)
        
        # Add timestamp and level
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        if level == "error":
            prefix = f"[{timestamp}] ❌ "
        elif level == "warning":
            prefix = f"[{timestamp}] ⚠️ "
        elif level == "success":
            prefix = f"[{timestamp}] ✅ "
        else:
            prefix = f"[{timestamp}] ℹ️ "
        
        self.details_text.insert(tk.END, f"{prefix}{message}\n")
        self.details_text.see(tk.END)
        self.details_text.config(state=tk.DISABLED)
        self.root.update()
    
    def _on_continue(self):
        """Handle continue button."""
        if self.startup_success:
            self.user_wants_to_continue = True
            self.root.destroy()
        else:
            self.root.destroy()
            sys.exit(1)
    
    def _on_exit(self):
        """Handle exit button."""
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        """Run the GUI."""
        self.add_detail("Starting Jarvis setup process...", "info")
        self.add_detail("Checking Python environment...", "info")
        self.add_detail("Checking dependencies...", "info")
        self.add_detail("Checking Ollama installation...", "info")
        self.add_detail("This may take a moment...", "info")
        
        self.root.mainloop()
        return self.user_wants_to_continue and self.startup_success

async def main():
    """Main function."""
    print("🤖 Jarvis AI Assistant - GUI Startup")
    print("=" * 50)
    
    try:
        # Create and run GUI
        gui = MainThreadGUI()
        gui.create_window()
        
        # Run GUI and get result
        success = gui.run()
        
        if success:
            print("✅ Setup completed successfully!")
            print("🚀 Starting Jarvis AI Assistant...")
            print()
            
            # Import and start main application
            from jarvis.main import main as jarvis_main
            await jarvis_main()
        else:
            print("❌ Setup was not completed successfully.")
            sys.exit(1)
            
    except ImportError as e:
        print(f"❌ Error importing Jarvis: {e}")
        print()
        print("This might be a dependency issue. Try:")
        print("1. Install dependencies: python install_py313.py")
        print("2. Or manually: pip install -r requirements-py313.txt")
        print("3. Check Python version (3.8+ required)")
        sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n👋 Jarvis stopped by user.")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Critical error starting Jarvis: {e}")
        print()
        print("Please check:")
        print("1. Python version (3.8+ required)")
        print("2. Dependencies installed")
        print("3. Ollama is installed and running")
        print("4. At least one model is downloaded")
        print()
        print("For detailed logs, check the logs/ directory")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
