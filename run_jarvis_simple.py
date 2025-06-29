#!/usr/bin/env python3
"""
Simple startup for Jarvis AI Assistant without GUI threading.
This version avoids tkinter threading issues entirely.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

async def simple_startup():
    """Simple startup without GUI threading."""
    print("🤖 Jarvis AI Assistant - Simple Startup")
    print("=" * 50)
    
    try:
        # Import components
        from jarvis.core.startup_manager import StartupManager
        from jarvis.main import main as jarvis_main
        
        print("✅ Imports successful")
        
        # Create startup manager
        startup_manager = StartupManager()
        
        # Run startup without GUI
        print("🔍 Running system checks...")
        success = await startup_manager.run_startup_process(show_gui=False)
        
        if success:
            print("\n✅ All checks passed!")
            print("🚀 Starting Jarvis AI Assistant...")
            print()
            
            # Start main application
            await jarvis_main()
        else:
            print("\n❌ Startup checks failed")
            print("Please ensure:")
            print("1. Ollama is installed: https://ollama.ai")
            print("2. At least one model is downloaded: ollama pull llama2")
            print("3. Dependencies are installed: pip install -r requirements-py313.txt")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTry the full startup: python run_jarvis.py")
        sys.exit(1)

def main():
    """Main entry point."""
    try:
        asyncio.run(simple_startup())
    except KeyboardInterrupt:
        print("\n👋 Jarvis stopped by user.")
    except Exception as e:
        print(f"❌ Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
