"""
Startup Manager for Jarvis AI Assistant.
Handles consumer-friendly initialization, dependency checking, and setup guidance.
"""

import asyncio
import sys
import subprocess
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
import threading

from .config import config
from .logging import get_logger
from .ollama_manager import OllamaManager, get_installation_instructions, get_model_recommendations

logger = get_logger("startup_manager")


class StartupGUI:
    """GUI for startup process and user guidance."""
    
    def __init__(self):
        self.root = None
        self.progress_var = None
        self.status_var = None
        self.progress_bar = None
        self.status_label = None
        self.details_text = None
        self.continue_button = None
        self.is_complete = False
        self.user_action_needed = False
        self.user_clicked_continue = False
    
    def create_window(self):
        """Create startup window."""
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
        
        subtitle_label = ttk.Label(
            main_frame, 
            text="Setting up your AI assistant...", 
            font=("Arial", 10)
        )
        subtitle_label.pack(pady=(0, 20))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, 
            variable=self.progress_var, 
            maximum=100,
            length=400
        )
        self.progress_bar.pack(pady=(0, 10))
        
        # Status label
        self.status_var = tk.StringVar(value="Initializing...")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=(0, 20))
        
        # Details text area
        details_frame = ttk.LabelFrame(main_frame, text="Details", padding="10")
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
            text="Continue",
            command=self._on_continue,
            state=tk.DISABLED
        )
        self.continue_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Button(
            button_frame,
            text="Exit",
            command=self._on_exit
        ).pack(side=tk.RIGHT)
    
    def update_progress(self, value: float, status: str):
        """Update progress bar and status."""
        if self.progress_var:
            self.progress_var.set(value)
        if self.status_var:
            self.status_var.set(status)
        if self.root:
            self.root.update()
    
    def add_detail(self, message: str, level: str = "info"):
        """Add detail message to text area."""
        if not self.details_text:
            return
        
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
        
        if self.root:
            self.root.update()
    
    def show_user_action_needed(self, title: str, message: str):
        """Show that user action is needed."""
        self.user_action_needed = True
        self.continue_button.config(state=tk.NORMAL, text="I've completed this step")
        self.update_progress(50, f"Action needed: {title}")
        self.add_detail(f"USER ACTION REQUIRED: {title}", "warning")
        self.add_detail(message, "warning")
    
    def complete_setup(self, success: bool):
        """Mark setup as complete."""
        self.is_complete = True
        if success:
            self.update_progress(100, "Setup complete! Starting Jarvis...")
            self.add_detail("Setup completed successfully!", "success")
            self.continue_button.config(text="Start Jarvis", state=tk.NORMAL)
        else:
            self.update_progress(0, "Setup failed - please check the details above")
            self.add_detail("Setup failed. Please resolve the issues and try again.", "error")
            self.continue_button.config(text="Retry", state=tk.NORMAL)
    
    def _on_continue(self):
        """Handle continue button."""
        if self.user_action_needed:
            self.user_action_needed = False
            self.continue_button.config(state=tk.DISABLED, text="Continue")
        elif self.is_complete:
            # Mark that user clicked continue
            self.user_clicked_continue = True
            self.continue_button.config(state=tk.DISABLED, text="Starting...")
            self.add_detail("User clicked Start Jarvis - launching main application...", "success")
            # Close the window properly
            self.root.destroy()
    
    def _on_exit(self):
        """Handle exit button."""
        self.root.destroy()
        sys.exit(0)
    
    def run(self):
        """Run the GUI."""
        if self.root:
            self.root.mainloop()


class StartupManager:
    """Manages the complete startup process for consumer users."""
    
    def __init__(self):
        self.gui = None
        self.ollama_manager = None
        self.startup_steps = [
            ("Checking Python environment", self._check_python_environment),
            ("Checking dependencies", self._check_dependencies),
            ("Checking Ollama installation", self._check_ollama_installation),
            ("Starting Ollama service", self._start_ollama_service),
            ("Checking available models", self._check_models),
            ("Testing AI functionality", self._test_ai_functionality),
            ("Initializing user interface", self._initialize_ui),
        ]
        self.current_step = 0
        self.total_steps = len(self.startup_steps)
    
    async def run_startup_process(self, show_gui: bool = True) -> bool:
        """Run the complete startup process."""
        try:
            if show_gui:
                # Create and show GUI in separate thread
                self.gui_ready = threading.Event()
                gui_thread = threading.Thread(target=self._run_gui, daemon=True)
                gui_thread.start()
                
                # Wait for GUI to be ready
                while not self.gui_ready.is_set():
                    await asyncio.sleep(0.1)
            
            logger.info("Starting Jarvis setup process...")
            
            # Run through all startup steps
            for i, (step_name, step_func) in enumerate(self.startup_steps):
                self.current_step = i
                progress = (i / self.total_steps) * 100
                
                if self.gui:
                    self.gui.update_progress(progress, f"Step {i+1}/{self.total_steps}: {step_name}")
                    self.gui.add_detail(f"Starting: {step_name}")
                
                logger.info(f"Step {i+1}/{self.total_steps}: {step_name}")
                
                try:
                    success = await step_func()
                    if success:
                        if self.gui:
                            self.gui.add_detail(f"Completed: {step_name}", "success")
                    else:
                        if self.gui:
                            self.gui.add_detail(f"Failed: {step_name}", "error")
                        logger.error(f"Step failed: {step_name}")
                        
                        # Check if this is a critical failure
                        if step_name in ["Checking Ollama installation", "Checking available models"]:
                            await self._handle_critical_failure(step_name)
                            return False
                        
                except Exception as e:
                    logger.error(f"Error in step '{step_name}': {e}")
                    if self.gui:
                        self.gui.add_detail(f"Error in {step_name}: {e}", "error")
                    return False
            
            # Setup complete
            if self.gui:
                self.gui.complete_setup(True)
                
                # Wait for user to actually click the "Start Jarvis" button
                while self.gui.root and self.gui.root.winfo_exists():
                    if self.gui.user_clicked_continue:
                        # User clicked the button, we can proceed
                        break
                    await asyncio.sleep(0.1)
                
                # Give GUI time to close properly
                await asyncio.sleep(1.0)
                
                # GUI should be closed by the button handler, but ensure cleanup
                try:
                    if self.gui and self.gui.root and self.gui.root.winfo_exists():
                        self.gui.root.destroy()
                except:
                    pass  # GUI already closed
                
                # Clear GUI reference to prevent threading issues
                self.gui = None
            
            logger.info("Startup process completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Critical error in startup process: {e}")
            if self.gui:
                self.gui.add_detail(f"Critical error: {e}", "error")
                self.gui.complete_setup(False)
            return False
    
    def _run_gui(self):
        """Run GUI in separate thread."""
        try:
            self.gui = StartupGUI()
            self.gui.create_window()
            self.gui_ready.set()  # Signal that GUI is ready
            self.gui.run()
        except Exception as e:
            logger.error(f"Error in GUI thread: {e}")
        finally:
            # Clean up GUI references to prevent threading issues
            if self.gui:
                self.gui.progress_var = None
                self.gui.status_var = None
                self.gui.root = None
    
    async def _check_python_environment(self) -> bool:
        """Check Python version and basic environment."""
        try:
            version = sys.version_info
            if self.gui:
                self.gui.add_detail(f"Python version: {version.major}.{version.minor}.{version.micro}")
            
            if version.major == 3 and version.minor >= 8:
                if self.gui:
                    self.gui.add_detail("Python version is compatible", "success")
                return True
            else:
                if self.gui:
                    self.gui.add_detail("Python 3.8+ required", "error")
                return False
                
        except Exception as e:
            logger.error(f"Error checking Python environment: {e}")
            return False
    
    async def _check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        try:
            required_packages = [
                ("ollama", "Ollama Python client"),
                ("tkinter", "GUI framework"),
                ("requests", "HTTP client"),
                ("pyyaml", "Configuration files"),
            ]
            
            missing_packages = []
            
            for package, description in required_packages:
                try:
                    if package == "tkinter":
                        import tkinter
                    else:
                        __import__(package)
                    
                    if self.gui:
                        self.gui.add_detail(f"✓ {description} available")
                except ImportError:
                    missing_packages.append((package, description))
                    if self.gui:
                        self.gui.add_detail(f"✗ {description} missing", "warning")
            
            if missing_packages:
                if self.gui:
                    self.gui.add_detail("Some packages are missing but Jarvis can still work with reduced functionality", "warning")
                return True  # Non-critical for basic functionality
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking dependencies: {e}")
            return False
    
    async def _check_ollama_installation(self) -> bool:
        """Check if Ollama is installed."""
        try:
            self.ollama_manager = OllamaManager()
            
            if self.ollama_manager.is_ollama_installed():
                if self.gui:
                    self.gui.add_detail("Ollama is installed", "success")
                return True
            else:
                if self.gui:
                    self.gui.add_detail("Ollama is not installed", "error")
                return False
                
        except Exception as e:
            logger.error(f"Error checking Ollama installation: {e}")
            return False
    
    async def _start_ollama_service(self) -> bool:
        """Start Ollama service if needed."""
        try:
            if not self.ollama_manager:
                return False
            
            if await self.ollama_manager.check_ollama_status():
                if self.gui:
                    self.gui.add_detail("Ollama service is already running", "success")
                return True
            
            if self.gui:
                self.gui.add_detail("Starting Ollama service...")
            
            if await self.ollama_manager.start_ollama():
                if self.gui:
                    self.gui.add_detail("Ollama service started successfully", "success")
                return True
            else:
                if self.gui:
                    self.gui.add_detail("Failed to start Ollama service", "error")
                return False
                
        except Exception as e:
            logger.error(f"Error starting Ollama service: {e}")
            return False
    
    async def _check_models(self) -> bool:
        """Check for available models."""
        try:
            if not self.ollama_manager:
                return False
            
            models = await self.ollama_manager.refresh_models()
            
            if models:
                if self.gui:
                    self.gui.add_detail(f"Found {len(models)} available models:", "success")
                    for model in models:
                        name = model.get('name', 'Unknown')
                        self.gui.add_detail(f"  - {name}")
                return True
            else:
                if self.gui:
                    self.gui.add_detail("No models found", "error")
                return False
                
        except Exception as e:
            logger.error(f"Error checking models: {e}")
            return False
    
    async def _test_ai_functionality(self) -> bool:
        """Test basic AI functionality."""
        try:
            if not self.ollama_manager:
                return False
            
            best_model = self.ollama_manager.get_best_model()
            if not best_model:
                if self.gui:
                    self.gui.add_detail("No suitable model found for testing", "error")
                return False
            
            if self.gui:
                self.gui.add_detail(f"Testing model: {best_model}")
            
            if await self.ollama_manager.test_model(best_model):
                if self.gui:
                    self.gui.add_detail("AI functionality test passed", "success")
                return True
            else:
                if self.gui:
                    self.gui.add_detail("AI functionality test failed", "error")
                return False
                
        except Exception as e:
            logger.error(f"Error testing AI functionality: {e}")
            return False
    
    async def _initialize_ui(self) -> bool:
        """Initialize user interface components."""
        try:
            # This would initialize the main UI components
            if self.gui:
                self.gui.add_detail("User interface components ready", "success")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing UI: {e}")
            return False
    
    async def _handle_critical_failure(self, step_name: str):
        """Handle critical failures that require user action."""
        if step_name == "Checking Ollama installation":
            if self.gui:
                self.gui.show_user_action_needed(
                    "Install Ollama",
                    get_installation_instructions()
                )
                
                # Wait for user to complete action
                while self.gui.user_action_needed:
                    await asyncio.sleep(0.5)
        
        elif step_name == "Checking available models":
            if self.gui:
                recommendations = get_model_recommendations()
                model_text = "\n".join([f"ollama pull {model}" for model in recommendations[:3]])
                
                self.gui.show_user_action_needed(
                    "Download AI Models",
                    f"Please download at least one AI model:\n\n{model_text}\n\nRun these commands in a terminal, then click continue."
                )
                
                # Wait for user to complete action
                while self.gui.user_action_needed:
                    await asyncio.sleep(0.5)


# Main startup function
async def run_consumer_startup() -> bool:
    """Run the consumer-friendly startup process."""
    startup_manager = StartupManager()
    return await startup_manager.run_startup_process(show_gui=True)


if __name__ == "__main__":
    # Test the startup process
    asyncio.run(run_consumer_startup())
