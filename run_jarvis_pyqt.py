#!/usr/bin/env python3
"""
Startup script for Jarvis AI Assistant with modern PyQt6 GUI.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def main():
    """Main startup function."""
    print("🤖 Jarvis AI Assistant - Modern PyQt6 GUI Startup")
    print("=" * 60)
    
    try:
        # Check PyQt6 availability
        try:
            from PyQt6.QtWidgets import QApplication
            print("✅ PyQt6 is available")
        except ImportError:
            print("❌ PyQt6 is not installed. Installing...")
            os.system("pip install PyQt6")
            try:
                from PyQt6.QtWidgets import QApplication
                print("✅ PyQt6 installed successfully")
            except ImportError:
                print("❌ Failed to install PyQt6. Please install manually: pip install PyQt6")
                return False
        
        # Import and run Jarvis
        from src.jarvis.main_pyqt import cli_main
        
        print("✅ Setup completed successfully!")
        print("🚀 Starting Jarvis AI Assistant with modern GUI...")
        print()
        
        # Start Jarvis
        cli_main()
        
    except KeyboardInterrupt:
        print("\n👋 Jarvis shutdown complete.")
    except Exception as e:
        print(f"❌ Error starting Jarvis: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
