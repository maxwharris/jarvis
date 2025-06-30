# 🤖 Jarvis AI Assistant

A powerful, privacy-focused AI assistant that runs entirely on your local machine using Ollama. Jarvis provides intelligent file management, screen analysis, voice interaction, app automation, and comprehensive task management while keeping all your data private and secure.

## ✨ Core Features

### 🧠 **AI-Powered Intelligence**
- **Local LLM Integration** - Powered by Ollama with support for multiple models (Qwen2.5, LLaMA, etc.)
- **Vision Capabilities** - Analyze screenshots and images with LLaVA
- **Conversation Memory** - Maintains context across interactions with SQLite database
- **Smart Action Recognition** - Automatically detects and executes file operations and app commands
- **Online/Offline Modes** - Toggle between local-only and web-enabled functionality

### 📁 **Advanced File Management**
- **Intelligent File Operations** - Copy, move, rename, and analyze files with natural language
- **Smart Directory Browsing** - List and explore folder contents with detailed analysis
- **File Search** - Find files by name, content, or properties
- **Safe Deletion** - Automatic backups before deletion with recovery options
- **File Analysis** - Detailed file properties, content preview, and metadata extraction
- **Batch Operations** - Process multiple files simultaneously
- **Path Intelligence** - Smart path resolution and validation

### 🖥️ **Screen Analysis & Automation**
- **Screenshot Capture** - Take and analyze screen contents with AI vision
- **Visual Understanding** - Describe applications, windows, and UI elements
- **UI Element Recognition** - Identify clickable elements, buttons, and interface components
- **Automated Analysis** - Process screenshots with vision models for detailed insights
- **Multi-Monitor Support** - Handle multiple display configurations

### 🎮 **App Automation & Control**
- **Application Launching** - Auto-launch applications when not running
- **Window Management** - Focus, switch, and control application windows
- **Discord Integration** - Send messages, join voice channels, manage Discord interactions
- **Spotify Control** - Play songs, control playback, search music library
- **Browser Automation** - Open websites, perform searches, manage tabs intelligently
- **System App Control** - Launch Calculator, Notepad, Command Prompt, and system utilities
- **Smart Tab Management** - New tabs for searches, current tab for navigation
- **Cross-App Workflows** - Chain actions across multiple applications

### 🎤 **Voice & Text Interaction**
- **Wake Word Detection** - Activate with "Hey Max" or custom wake words
- **Speech-to-Text** - Convert voice commands to text with high accuracy
- **Text-to-Speech** - Spoken responses with configurable voices and settings
- **Hotkey Support** - Quick text input with Ctrl+Alt+J and customizable shortcuts
- **Multiple Input Methods** - Voice, text, GUI, and system tray interaction
- **Voice Command Processing** - Natural language understanding for complex commands

### 🌐 **Web Integration & Search**
- **Intelligent Web Search** - Context-aware search with multiple search engines
- **Privacy Controls** - Easily toggle online/offline modes with visual indicators
- **Search Engine Selection** - Google, Bing, DuckDuckGo support
- **Smart URL Handling** - Automatic protocol detection and URL validation
- **New Tab Management** - Searches open in new tabs, navigation uses current tab
- **Web Content Analysis** - Process and understand web page content

### 👤 **User Profile & Personalization**
- **User Profile System** - Personalized settings and preferences
- **Conversation History** - Searchable chat history with full-text search
- **Custom Preferences** - Tailored responses based on user behavior
- **Settings Management** - Comprehensive configuration through GUI
- **Profile Persistence** - Settings saved across sessions
- **Multi-User Support** - Individual profiles for different users

### 🗄️ **Database & Data Management**
- **SQLite Integration** - Robust local database for conversation storage
- **Conversation Logging** - Optional detailed interaction history
- **Data Export/Import** - Backup and restore conversation data
- **Search Functionality** - Find past conversations and interactions
- **Data Integrity** - Automatic database maintenance and repair
- **Privacy Controls** - Full control over data retention and deletion

### 🔒 **Privacy & Security**
- **100% Local Processing** - No data sent to external servers by default
- **Offline by Default** - Works completely offline with optional online features
- **Conversation Encryption** - Optional encryption for sensitive data
- **Safe Path Validation** - Prevents access to system directories
- **Audit Logging** - Comprehensive operation tracking
- **Secure Automation** - Safety checks for UI automation and app control

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+** (Python 3.13 fully supported)
- **Ollama** - Download from [ollama.ai](https://ollama.ai)
- **Windows 11** (primary support, Windows 10 compatible)
- **8GB RAM minimum** (16GB recommended for optimal performance)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd jarvis
   ```

2. **Install dependencies:**
   ```bash
   # For Python 3.13 (recommended)
   pip install -r requirements-py313.txt
   
   # For Python 3.11/3.12
   pip install -r requirements.txt
   
   # For UI automation features (optional)
   pip install pyautogui pygetwindow
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
   # PyQt6 GUI (recommended)
   python run_jarvis_pyqt.py
   
   # Console version
   python run_jarvis.py
   ```

## 🎯 Usage Examples

### File Management
```
"list files in documents"
"copy report.pdf to backup folder"
"move old photos to archive"
"analyze this document"
"search for python files in projects"
"delete temporary files older than 30 days"
"show me the largest files in downloads"
```

### App Automation
```
"message john on discord"
"play bohemian rhapsody by queen on spotify"
"open calculator"
"search for python tutorials"
"open github.com in new tab"
"join general voice channel on discord"
"pause spotify"
"switch to notepad"
```

### Screen Analysis
```
"take a screenshot"
"analyze my screen"
"what's on my screen?"
"describe what you see"
"find the login button"
"click on the search box"
```

### Web & Search
```
"search for machine learning tutorials"
"search for weather forecast on bing"
"open youtube.com"
"go to reddit.com"
"find information about AI development"
```

### Voice Commands
```
"Hey Max, list my desktop files"
"Hey Max, take a screenshot and analyze it"
"Hey Max, play my favorite playlist on spotify"
"Hey Max, message sarah on discord saying hello"
"Hey Max, what's the weather like?" (online mode)
```

### System Control
```
"system status"
"how is my computer performing?"
"show system info"
"open task manager"
"launch command prompt"
"switch windows"
```

## ⚙️ Configuration

### Main Configuration (`config/settings.yaml`)

```yaml
# AI Models
models:
  text_model: "qwen2.5:14b"
  vision_model: "llava:latest"
  ollama_host: "http://localhost:11434"
  temperature: 0.7
  max_tokens: 2048

# Voice Settings
voice:
  enabled: false  # Set to true to enable voice features
  wake_word: "hey max"
  tts_engine: "pyttsx3"
  voice_rate: 200
  voice_volume: 0.8

# Privacy & Online Settings
privacy:
  online_mode: false  # Enable for web search and online features
  log_conversations: true
  confirm_dangerous_actions: true
  encrypt_conversations: false

# UI Automation Settings
automation:
  enabled: true  # Enable app automation features
  safety_checks: true
  auto_launch_apps: true
  screenshot_analysis: true

# UI Settings
ui:
  theme: "dark"
  system_tray: true
  startup_notification: true
  window_size: [1000, 700]
  font_size: 12

# Database Settings
database:
  path: "data/jarvis.db"
  backup_enabled: true
  max_conversations: 10000
  cleanup_old_data: true
```

### User Profile Configuration (`config/user_profile.json`)
```json
{
  "name": "User",
  "preferences": {
    "response_style": "helpful",
    "verbosity": "medium",
    "preferred_search_engine": "google",
    "default_browser": "chrome"
  },
  "automation_settings": {
    "auto_launch_apps": true,
    "confirm_actions": true,
    "preferred_apps": {
      "music": "spotify",
      "chat": "discord",
      "browser": "chrome"
    }
  }
}
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
│   ├── ollama_manager.py  # Ollama server management
│   ├── startup_manager.py # Application startup & initialization
│   └── user_profile.py    # User profile & personalization
├── input/                 # Input handlers
│   ├── voice_handler.py   # Voice processing & wake words
│   └── text_handler.py    # Text input & hotkeys
├── output/                # Output managers
│   ├── tts_engine.py      # Text-to-speech
│   ├── ui_manager_pyqt.py # PyQt6 GUI with modern interface
│   └── ui_manager.py      # Base UI manager
├── tools/                 # Action & automation system
│   ├── action_dispatcher.py # File ops, screen capture, system info
│   ├── ui_automator.py    # UI automation & screen analysis
│   └── app_automators.py  # App-specific automation (Discord, Spotify, etc.)
└── ui/                    # User interface components
    ├── settings_window.py # Comprehensive settings GUI
    └── __init__.py        # UI module initialization
```

### Key Features

- **Modular Design** - Easy to extend and customize
- **Async Processing** - Non-blocking operations for smooth UI
- **Comprehensive Error Handling** - Robust error recovery and logging
- **Advanced Logging System** - Detailed operation tracking with SQLite
- **Multi-Layer Safety** - Path validation, backups, and confirmation dialogs
- **Plugin Architecture** - Extensible automation system

## 🔧 Advanced Features

### App Automation System
- **Auto-Launch Applications** - Automatically starts apps when needed
- **Window Focus Management** - Smart window switching and focus control
- **Cross-App Integration** - Seamless workflows between applications
- **Pattern Recognition** - Natural language command interpretation
- **Safety Mechanisms** - Prevents dangerous automation actions

### Database & Conversation Management
- **SQLite Integration** - Robust local database with full-text search
- **Conversation Threading** - Organized chat history with context
- **Data Export/Import** - Backup and restore functionality
- **Search & Filter** - Find specific conversations and interactions
- **Automatic Cleanup** - Configurable data retention policies

### Screen Analysis & Vision
- **AI-Powered Screenshot Analysis** - Detailed understanding of screen content
- **UI Element Detection** - Identify buttons, forms, and interactive elements
- **Application Recognition** - Detect running applications and their states
- **Multi-Monitor Support** - Handle complex display configurations
- **Visual Context Understanding** - Interpret visual information for automation

### User Profile & Personalization
- **Adaptive Responses** - Learn from user interactions and preferences
- **Custom Settings** - Personalized configuration for each user
- **Behavior Tracking** - Optional usage analytics for improvement
- **Profile Switching** - Support for multiple user profiles
- **Preference Learning** - Automatic adaptation to user patterns

### Web Integration & Privacy
- **Smart Online/Offline Toggle** - Visual indicators and easy switching
- **Privacy-First Design** - Local processing with optional online features
- **Search Engine Selection** - Multiple search providers with user choice
- **Content Filtering** - Safe browsing with content analysis
- **Data Minimization** - Only necessary data is processed or stored

## 📊 Performance & System Requirements

### Minimum Requirements
- **OS**: Windows 10/11 (primary), Linux (experimental)
- **RAM**: 8GB (16GB recommended for optimal performance)
- **Storage**: 15GB (10GB for models, 5GB for application and data)
- **CPU**: Modern multi-core processor (Intel i5/AMD Ryzen 5 or better)
- **Network**: Internet connection for initial model download and optional online features

### Recommended Configuration
- **RAM**: 16GB+ for smooth multi-model operation
- **Storage**: SSD for faster model loading and database operations
- **GPU**: NVIDIA GPU with 8GB+ VRAM for accelerated AI processing
- **CPU**: Intel i7/AMD Ryzen 7 or better for responsive automation

### Model Performance
- **qwen2.5:14b**: Excellent reasoning and conversation, 6-12GB RAM usage
- **llava:latest**: Advanced vision analysis, 4-8GB RAM usage
- **Response Times**: 1-5 seconds depending on complexity and hardware
- **Concurrent Operations**: Supports multiple simultaneous tasks

## 🛠️ Development & Testing

### Development Setup
```bash
# Clone and setup development environment
git clone <repository-url>
cd jarvis
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-py313.txt

# Enable debug mode
export JARVIS_DEBUG=true  # On Windows: set JARVIS_DEBUG=true
python run_jarvis_pyqt.py
```

### Testing Suite
```bash
# Test core functionality
python test_fixes.py

# Test app automation
python test_app_automation.py

# Test enhanced automation features
python test_enhanced_automation.py

# Test pattern matching fixes
python test_pattern_fixes.py

# Test database functionality
python test_database_fix.py

# Test user profile system
python test_user_system.py

# Test online/offline sync
python test_online_offline_sync.py
```

### Adding New Features
1. **New Automation Patterns** - Add to `app_automators.py`
2. **Custom Actions** - Extend `action_dispatcher.py`
3. **UI Components** - Add to `ui/` directory
4. **Configuration Options** - Update settings files
5. **Database Schema** - Modify database initialization

## 🔐 Privacy & Security Details

### Data Handling Philosophy
- **Local-First**: All processing happens on your machine by default
- **Opt-In Online**: Web features require explicit user activation
- **Transparent Logging**: Full visibility into what data is stored
- **User Control**: Complete control over data retention and deletion
- **No Telemetry**: No usage data sent to external servers

### Security Features
- **Path Validation** - Prevents unauthorized file system access
- **Operation Sandboxing** - Isolated execution of potentially dangerous operations
- **Backup System** - Automatic backups before destructive file operations
- **Audit Trail** - Comprehensive logging of all system interactions
- **Safe Automation** - Multiple safety checks for UI automation
- **Encrypted Storage** - Optional encryption for sensitive conversation data

### Privacy Controls
- **Online Mode Toggle** - Easy switching between local and web-enabled modes
- **Conversation Logging** - Optional with granular control
- **Data Export** - Full data portability and backup options
- **Selective Deletion** - Remove specific conversations or data types
- **Anonymous Mode** - Option to disable all logging and personalization

## 🎯 Use Cases & Workflows

### Personal Productivity
- **File Organization** - Intelligent file management and cleanup
- **Task Automation** - Streamline repetitive computer tasks
- **Research Assistance** - Web search and information gathering
- **Document Analysis** - Extract insights from files and screenshots
- **Communication Management** - Automate messaging and social interactions

### Development & Technical Work
- **Code Project Management** - Organize and analyze code repositories
- **System Administration** - Monitor system performance and manage processes
- **Documentation** - Generate and maintain technical documentation
- **Testing & Debugging** - Analyze screenshots and system states
- **Environment Setup** - Automate development environment configuration

### Content Creation & Media
- **Media Organization** - Sort and manage photos, videos, and documents
- **Content Research** - Gather information and references
- **Social Media Management** - Automate posting and engagement
- **Music & Entertainment** - Control media playback and discovery
- **Creative Workflows** - Streamline design and content creation processes

### Business & Professional
- **Meeting Preparation** - Organize files and research topics
- **Report Generation** - Analyze data and create summaries
- **Communication Automation** - Manage professional messaging
- **Presentation Support** - Gather materials and organize content
- **Data Analysis** - Process and interpret business information

## 🤝 Contributing

We welcome contributions to make Jarvis even better! Here's how you can help:

### Development Contributions
- **Bug Fixes** - Report and fix issues
- **Feature Development** - Add new automation capabilities
- **Performance Improvements** - Optimize existing functionality
- **Documentation** - Improve guides and examples
- **Testing** - Expand test coverage and quality assurance

### Community Contributions
- **User Guides** - Create tutorials and how-to content
- **Use Case Examples** - Share creative automation workflows
- **Feedback & Suggestions** - Help prioritize new features
- **Translation** - Localize for different languages
- **Platform Support** - Extend compatibility to other operating systems

### Getting Started with Development
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request with detailed description
5. Participate in code review process

## 📚 Documentation & Resources

### Available Documentation
- **Installation Guide** - Detailed setup instructions
- **User Manual** - Comprehensive usage documentation
- **API Reference** - Technical documentation for developers
- **Automation Guide** - Advanced automation patterns and examples
- **Troubleshooting** - Common issues and solutions

### Community Resources
- **GitHub Discussions** - Community Q&A and feature requests
- **Issue Tracker** - Bug reports and feature requests
- **Wiki** - Community-maintained documentation
- **Examples Repository** - Sample configurations and workflows

## 🔧 Troubleshooting

### Common Issues

#### Ollama Connection Problems
```bash
# Check if Ollama is running
ollama list

# Restart Ollama service
ollama serve

# Verify model availability
ollama pull qwen2.5:14b
```

#### Voice Recognition Issues
- Ensure microphone permissions are granted
- Check audio device settings in system preferences
- Verify wake word sensitivity in configuration
- Test with different microphones or audio inputs

#### App Automation Not Working
- Install automation dependencies: `pip install pyautogui pygetwindow`
- Check Windows permissions for automation
- Verify target applications are installed and accessible
- Review automation safety settings in configuration

#### Performance Issues
- Increase system RAM allocation
- Use SSD storage for better model loading
- Close unnecessary applications
- Adjust model parameters for your hardware

### Getting Help
- **GitHub Issues** - Report bugs and request features
- **Discussions** - Ask questions and get community support
- **Documentation** - Check comprehensive guides and examples
- **Logs** - Review application logs for detailed error information

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Third-Party Licenses
- **Ollama** - Apache 2.0 License
- **PyQt6** - GPL v3 / Commercial License
- **SQLite** - Public Domain
- **Various Python packages** - See individual package licenses

## 🙏 Acknowledgments

### Core Technologies
- **[Ollama](https://ollama.ai)** - For providing excellent local LLM infrastructure
- **[PyQt6](https://www.riverbankcomputing.com/software/pyqt/)** - For the robust GUI framework
- **[LLaVA](https://llava-vl.github.io/)** - For advanced vision-language capabilities
- **[Qwen](https://qwen.readthedocs.io/)** - For powerful language understanding

### Community & Inspiration
- **Open Source Community** - For tools, libraries, and inspiration
- **AI Research Community** - For advancing the field of AI assistants
- **Privacy Advocates** - For emphasizing the importance of local AI processing
- **Beta Testers** - For feedback and bug reports during development

### Special Thanks
- Contributors who have helped improve Jarvis
- Users who provide feedback and feature requests
- The broader AI and open source communities
- Everyone working to make AI more accessible and privacy-focused

## 📞 Support & Contact

### Getting Support
- **GitHub Issues** - Primary support channel for bugs and features
- **GitHub Discussions** - Community Q&A and general help
- **Documentation** - Comprehensive guides in the `docs/` folder
- **Wiki** - Community-maintained tips and tricks

### Feature Requests
- Use GitHub Issues with the "enhancement" label
- Provide detailed use cases and examples
- Check existing requests to avoid duplicates
- Participate in discussions about proposed features

### Security Issues
- Report security vulnerabilities privately via GitHub Security tab
- Include detailed reproduction steps
- Allow reasonable time for fixes before public disclosure

---

**Jarvis AI Assistant** - Your intelligent, private, local AI companion. 🤖✨

*Built with privacy in mind, powered by local AI, designed for productivity.*
