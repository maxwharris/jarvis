#!/usr/bin/env python3
"""
Consumer-friendly entry point for Jarvis AI Assistant.
Includes automatic setup, dependency checking, and user guidance.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main entry point with consumer-friendly startup."""
    try:
        # Import after path setup
        from jarvis.core.startup_manager import run_consumer_startup
        from jarvis.main import main as jarvis_main
        
        print("🤖 Jarvis AI Assistant")
        print("=" * 50)
        print("Starting consumer-friendly setup process...")
        print()
        
        # Run the consumer startup process
        print("Running startup process...")
        startup_success = asyncio.run(run_consumer_startup())
        
        if startup_success:
            print("\n✅ Setup completed successfully!")
            print("🚀 Starting Jarvis AI Assistant...")
            print("Please wait while Jarvis initializes...")
            print()
            
            try:
                # Start the main Jarvis application
                print("Launching main application...")
                asyncio.run(jarvis_main())
            except Exception as e:
                print(f"❌ Error starting main application: {e}")
                print("\nTroubleshooting:")
                print("1. Check logs in the logs/ directory")
                print("2. Try quick start: python run_jarvis.py --quick")
                print("3. Run diagnostics: python test_jarvis_startup.py")
                sys.exit(1)
        else:
            print("\n❌ Setup failed. Please resolve the issues above and try again.")
            print("\nFor help:")
            print("1. Make sure Ollama is installed: https://ollama.ai")
            print("2. Download a model: ollama pull llama2")
            print("3. Check the setup guide: README_Python313.md")
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

def quick_start():
    """Quick start without GUI setup (for advanced users)."""
    try:
        from jarvis.main import main as jarvis_main
        print("🤖 Jarvis AI Assistant - Quick Start")
        print("Skipping setup GUI...")
        asyncio.run(jarvis_main())
    except Exception as e:
        print(f"Error in quick start: {e}")
        print("Try running with full setup: python run_jarvis.py")
        sys.exit(1)

if __name__ == "__main__":
    # Check for quick start flag
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_start()
    else:
        main()
