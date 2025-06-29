# 🤖 Jarvis AI Assistant

A powerful, privacy-focused AI assistant that runs entirely on your local machine using Ollama. Jarvis provides intelligent file management, screen analysis, voice interaction, and task automation while keeping all your data private and secure.

## ✨ Features

### 🧠 **AI-Powered Intelligence**
- **Local LLM Integration** - Powered by Ollama with support for multiple models
- **Vision Capabilities** - Analyze screenshots and images with LLaVA
- **Conversation Memory** - Maintains context across interactions
- **Smart Action Recognition** - Automatically detects and executes file operations

### 📁 **Advanced File Management**
- **Intelligent File Operations** - Copy, move, rename, and analyze files
- **Smart Directory Browsing** - List and explore folder contents
- **File Search** - Find files by name or content
- **Safe Deletion** - Automatic backups before deletion
- **File Analysis** - Detailed file properties and content preview

### 🖥️ **Screen Analysis & Automation**
- **Screenshot Capture** - Take and analyze screen contents
- **Visual Understanding** - Describe what's visible on your screen
- **UI Element Recognition** - Identify applications, windows, and content
- **Automated Analysis** - Process screenshots with vision models

### 🎤 **Voice & Text Interaction**
- **Wake Word Detection** - Activate with "Hey Max"
- **Speech-to-Text** - Convert voice commands to text
- **Text-to-Speech** - Spoken responses (configurable)
- **Hotkey Support** - Quick text input with Ctrl+Alt+J
- **Multiple Input Methods** - Voice, text, and GUI interaction

### 🌐 **Web Integration** (Optional)
- **Web Search** - Search the internet when online mode is enabled
- **Privacy Controls** - Easily toggle online/offline modes
- **DuckDuckGo Integration** - Privacy-focused search results

### 🔒 **Privacy & Security**
- **100% Local Processing** - No data sent to external servers
- **Offline by Default** - Works completely offline
- **Conversation Logging** - Optional with full user control
- **Safe Path Validation** - Prevents access to system directories
- **Encrypted Storage** - Optional log encryption

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (Python 3.13 supported)
- **Ollama** - Download from [ollama.ai](https://ollama.ai)
- **Windows 11** (primary support)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd jarvis
   ```

2. **Install dependencies:**
   ```bash
   # For Python 3.13
   pip install -r requirements-py313.txt
   
   # For Python 3.11/3.12
   pip install -r requirements.txt
   ```

3. **Install and start Ollama:**
   ```bash
   # Download Ollama from https://ollama.ai
   # Then pull required models:
   ollama pull qwen2.5:14b
   ollama pull llava:latest
   ollama pull nomic-embed-text
   ```

4. **Run Jarvis:**
   ```bash
   python run_jarvis_pyqt.py
   ```

## 🎯 Usage Examples

### File Management
```
"list files in documents"
"copy report.pdf to backup folder"
"move old photos to archive"
"analyze this document"
"search for python files in projects"
```

### Screen Analysis
```
"take a screenshot"
"analyze my screen"
"what's on my screen?"
"describe what you see"
```

### System Information
```
"system status"
"how is my computer performing?"
"show system info"
```

### Voice Commands
```
"Hey Max, list my desktop files"
"Hey Max, take a screenshot and analyze it"
"Hey Max, what's the weather like?" (online mode)
```

## ⚙️ Configuration

### Main Configuration (`config/settings.yaml`)

```yaml
# AI Models
models:
  text_model: "qwen2.5:14b"
  vision_model: "llava:latest"
  ollama_host: "http://localhost:11434"

# Voice Settings (can be disabled)
voice:
  enabled: false  # Set to true to enable voice features
  wake_word: "hey max"
  tts_engine: "pyttsx3"

# Privacy Settings
privacy:
  online_mode: false  # Enable for web search
  log_conversations: true
  confirm_dangerous_actions: true

# UI Settings
ui:
  theme: "dark"
  system_tray: true
  startup_notification: true
```

### Model Configuration (`config/models.yaml`)
- Detailed model settings and performance profiles
- Custom model configurations
- Performance optimization settings

## 🏗️ Architecture

### Core Components

```
src/jarvis/
├── core/                   # Core functionality
│   ├── ai_engine.py       # Ollama integration & AI processing
│   ├── config.py          # Configuration management
│   ├── logging.py         # Logging & conversation history
│   └── ollama_manager.py  # Ollama server management
├── input/                 # Input handlers
│   ├── voice_handler.py   # Voice processing & wake words
│   └── text_handler.py    # Text input & hotkeys
├── output/                # Output managers
│   ├── tts_engine.py      # Text-to-speech
│   ├── ui_manager_pyqt.py # PyQt6 GUI
│   └── ui_manager.py      # Base UI manager
└── tools/                 # Action system
    └── action_dispatcher.py # File ops, screen capture, etc.
```

### Key Features

- **Modular Design** - Easy to extend and customize
- **Async Processing** - Non-blocking operations
- **Error Handling** - Comprehensive error recovery
- **Logging System** - Detailed operation tracking
- **Safety Mechanisms** - Path validation and backups

## 🔧 Advanced Features

### Temporary File Management
- Automatic cleanup of old files
- Organized temp folder structure
- Size monitoring and management

### Action Recognition
- Pattern-based command detection
- Natural language processing
- Context-aware responses

### Screen Capture System
- High-quality screenshot capture
- Optimized image processing for AI analysis
- Automatic temp file management

### Safety Systems
- Restricted path protection
- Automatic file backups
- Confirmation for dangerous operations
- Comprehensive audit logging

## 🛠️ Development

### Running in Development Mode
```bash
# Enable debug logging
export JARVIS_DEBUG=true
python run_jarvis_pyqt.py
```

### Testing
```bash
# Run action dispatcher tests
python -m src.jarvis.tools.action_dispatcher

# Test individual components
python -c "from src.jarvis.core.ai_engine import ai_engine; print(ai_engine.get_model_status())"
```

### Adding New Actions
1. Add pattern to `action_dispatcher.py`
2. Implement handler method
3. Add response formatting
4. Update documentation

## 📊 Performance

### System Requirements
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB for models, 1GB for application
- **CPU**: Modern multi-core processor
- **GPU**: Optional, CUDA support for faster processing

### Model Performance
- **qwen2.5:14b**: Excellent reasoning, 4-8GB VRAM
- **llava:latest**: Good vision analysis, 6-10GB VRAM
- **Response Times**: 1-5 seconds depending on complexity

## 🔐 Privacy & Security

### Data Handling
- **No External Servers** - Everything runs locally
- **Optional Logging** - Full user control over data retention
- **Encrypted Storage** - Optional encryption for sensitive data
- **Safe Defaults** - Privacy-first configuration

### Security Features
- **Path Validation** - Prevents unauthorized file access
- **Operation Logging** - Audit trail for all actions
- **Backup System** - Automatic backups before destructive operations
- **Sandboxed Operations** - Isolated temp file processing

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for:
- Code style and standards
- Testing requirements
- Documentation updates
- Feature requests and bug reports

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Ollama** - For providing excellent local LLM infrastructure
- **PyQt6** - For the robust GUI framework
- **LLaVA** - For vision-language capabilities
- **Qwen** - For powerful language understanding

## 📞 Support

- **Issues**: Report bugs and request features via GitHub Issues
- **Documentation**: Check the `docs/` folder for detailed guides
- **Community**: Join our discussions for help and tips

---

**Jarvis AI Assistant** - Your intelligent, private, local AI companion. 🤖✨
