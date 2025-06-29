#!/usr/bin/env python3
"""
Installation script for Jarvis AI Assistant on Python 3.13
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 8:
        print("✅ Python version is compatible")
        return True
    else:
        print("❌ Python 3.8+ required")
        return False

def install_dependencies():
    """Install Python dependencies."""
    requirements_file = "requirements-py313.txt"
    
    if not Path(requirements_file).exists():
        print(f"❌ {requirements_file} not found")
        return False
    
    # Try to install each package individually to handle failures gracefully
    packages = [
        "ollama>=0.1.7",
        "sounddevice>=0.4.6", 
        "numpy>=1.24.0",
        "webrtcvad>=2.0.10",
        "pyttsx3>=2.90",
        "Pillow>=10.0.0",
        "requests>=2.31.0",
        "keyboard>=0.13.5",
        "psutil>=5.9.0",
        "plyer>=2.1.0",
        "pyyaml>=6.0.1",
        "python-dateutil>=2.8.2",
        "colorama>=0.4.6"
    ]
    
    failed_packages = []
    
    for package in packages:
        print(f"\nInstalling {package}...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], 
                         check=True, capture_output=True, text=True)
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to install {package}: {e.stderr}")
            failed_packages.append(package)
    
    if failed_packages:
        print(f"\n⚠️ Some packages failed to install: {failed_packages}")
        print("Jarvis will still work with reduced functionality.")
    
    return len(failed_packages) < len(packages) // 2  # Success if more than half installed

def check_ollama():
    """Check if Ollama is available."""
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Ollama is installed")
            return True
        else:
            print("❌ Ollama not found")
            return False
    except FileNotFoundError:
        print("❌ Ollama not found in PATH")
        return False

def main():
    """Main installation process."""
    print("🤖 Jarvis AI Assistant - Python 3.13 Installation")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Critical dependencies failed to install")
        print("You may need to install some packages manually or use a different Python version")
        sys.exit(1)
    
    # Check Ollama
    if not check_ollama():
        print("\n⚠️ Ollama not found!")
        print("Please install Ollama from: https://ollama.ai")
        print("Then run: ollama pull llama2")
    
    print("\n🎉 Installation completed!")
    print("\nNext steps:")
    print("1. Make sure Ollama is running: ollama serve")
    print("2. Pull a model: ollama pull llama2")
    print("3. Start Jarvis: python run_jarvis.py")
    print("\nNote: Some advanced features may be limited due to Python 3.13 compatibility")

if __name__ == "__main__":
    main()
