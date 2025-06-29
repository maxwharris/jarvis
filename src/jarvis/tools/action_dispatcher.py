"""
Enhanced Action dispatcher for Jarvis AI Assistant.
Handles comprehensive file operations, screen analysis, and temp file management.
"""

import asyncio
import re
import os
import shutil
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
import time
from datetime import datetime, timedelta
import psutil
import tempfile

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from PIL import ImageGrab
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False

from ..core.config import config
from ..core.logging import get_logger, log_performance
from ..core.ai_engine import ai_engine

logger = get_logger("action_dispatcher")


class TempFileManager:
    """Manages temporary files and folders for Jarvis."""
    
    def __init__(self):
        self.temp_root = Path("jarvis/temp")
        self.setup_temp_structure()
        self.cleanup_interval = 24  # hours
        self.max_size_mb = 1024  # 1GB max temp storage
    
    def setup_temp_structure(self):
        """Create temp folder structure."""
        try:
            folders = [
                "screenshots",
                "downloads", 
                "analysis",
                "cache",
                "exports"
            ]
            
            for folder in folders:
                folder_path = self.temp_root / folder
                folder_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Temp folder structure created at: {self.temp_root}")
            
        except Exception as e:
            logger.error(f"Error creating temp structure: {e}")
    
    def get_screenshot_path(self) -> Path:
        """Get path for new screenshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.temp_root / "screenshots" / f"screenshot_{timestamp}.png"
    
    def get_analysis_path(self, filename: str) -> Path:
        """Get path for analysis output."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self.temp_root / "analysis" / f"{filename}_{timestamp}.json"
    
    def get_cache_path(self, filename: str) -> Path:
        """Get path for cache file."""
        return self.temp_root / "cache" / filename
    
    def cleanup_old_files(self, hours: int = None) -> Dict[str, Any]:
        """Clean up old temporary files."""
        try:
            if hours is None:
                hours = self.cleanup_interval
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            deleted_files = []
            total_size_freed = 0
            
            for folder in self.temp_root.iterdir():
                if folder.is_dir():
                    for file in folder.iterdir():
                        if file.is_file():
                            file_time = datetime.fromtimestamp(file.stat().st_mtime)
                            if file_time < cutoff_time:
                                size = file.stat().st_size
                                file.unlink()
                                deleted_files.append(str(file))
                                total_size_freed += size
            
            return {
                "success": True,
                "deleted_files": len(deleted_files),
                "size_freed_mb": round(total_size_freed / (1024 * 1024), 2),
                "files": deleted_files
            }
            
        except Exception as e:
            logger.error(f"Error cleaning temp files: {e}")
            return {"success": False, "error": str(e)}
    
    def get_temp_info(self) -> Dict[str, Any]:
        """Get information about temp folder usage."""
        try:
            total_size = 0
            file_counts = {}
            
            for folder in self.temp_root.iterdir():
                if folder.is_dir():
                    folder_size = 0
                    file_count = 0
                    
                    for file in folder.iterdir():
                        if file.is_file():
                            folder_size += file.stat().st_size
                            file_count += 1
                    
                    total_size += folder_size
                    file_counts[folder.name] = {
                        "files": file_count,
                        "size_mb": round(folder_size / (1024 * 1024), 2)
                    }
            
            return {
                "success": True,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "folders": file_counts,
                "temp_root": str(self.temp_root)
            }
            
        except Exception as e:
            logger.error(f"Error getting temp info: {e}")
            return {"success": False, "error": str(e)}


class SafetyManager:
    """Manages safety and security for file operations."""
    
    def __init__(self):
        # Restricted paths that should never be modified
        self.restricted_paths = [
            "C:/Windows",
            "C:/Program Files", 
            "C:/Program Files (x86)",
            "/System",
            "/usr",
            "/bin",
            "/sbin",
            "/etc"
        ]
        
        # Operations that require confirmation
        self.dangerous_operations = ["delete", "move", "copy"]
    
    def validate_path(self, path: str) -> Dict[str, Any]:
        """Validate if path is safe to operate on."""
        try:
            path_obj = Path(path).resolve()
            path_str = str(path_obj)
            
            # Check restricted paths
            for restricted in self.restricted_paths:
                if path_str.startswith(restricted):
                    return {
                        "safe": False,
                        "reason": f"Path is in restricted directory: {restricted}"
                    }
            
            # Check if path exists
            if not path_obj.exists():
                return {
                    "safe": False,
                    "reason": f"Path does not exist: {path}"
                }
            
            return {"safe": True, "resolved_path": str(path_obj)}
            
        except Exception as e:
            return {
                "safe": False,
                "reason": f"Invalid path: {e}"
            }
    
    def requires_confirmation(self, operation: str) -> bool:
        """Check if operation requires user confirmation."""
        return operation.lower() in self.dangerous_operations


class AdvancedFileManager:
    """Enhanced file management with comprehensive operations."""
    
    def __init__(self, temp_manager: TempFileManager, safety_manager: SafetyManager):
        self.temp_manager = temp_manager
        self.safety_manager = safety_manager
        self.operation_history = []
    
    async def list_files(self, directory: str, pattern: str = "*", recursive: bool = False) -> Dict[str, Any]:
        """List files in directory with enhanced information."""
        try:
            # Validate path
            validation = self.safety_manager.validate_path(directory)
            if not validation["safe"]:
                return {"success": False, "error": validation["reason"]}
            
            path = Path(validation["resolved_path"])
            
            if not path.is_dir():
                return {"success": False, "error": f"Not a directory: {directory}"}
            
            files = []
            dirs = []
            total_size = 0
            
            if recursive:
                items = path.rglob(pattern)
            else:
                items = path.glob(pattern)
            
            for item in items:
                try:
                    stat = item.stat()
                    item_info = {
                        "name": item.name,
                        "path": str(item),
                        "size": stat.st_size,
                        "size_human": self._format_size(stat.st_size),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "extension": item.suffix.lower() if item.is_file() else None
                    }
                    
                    if item.is_file():
                        files.append(item_info)
                        total_size += stat.st_size
                    elif item.is_dir():
                        dirs.append(item_info)
                        
                except (PermissionError, OSError):
                    # Skip files we can't access
                    continue
            
            # Sort files and directories
            files.sort(key=lambda x: x["name"].lower())
            dirs.sort(key=lambda x: x["name"].lower())
            
            return {
                "success": True,
                "directory": str(path),
                "files": files,
                "directories": dirs,
                "total_files": len(files),
                "total_directories": len(dirs),
                "total_size": total_size,
                "total_size_human": self._format_size(total_size),
                "recursive": recursive
            }
            
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return {"success": False, "error": str(e)}
    
    async def copy_file(self, source: str, destination: str) -> Dict[str, Any]:
        """Copy file or directory."""
        try:
            # Validate paths
            source_validation = self.safety_manager.validate_path(source)
            if not source_validation["safe"]:
                return {"success": False, "error": f"Source: {source_validation['reason']}"}
            
            source_path = Path(source_validation["resolved_path"])
            dest_path = Path(destination).expanduser().resolve()
            
            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Perform copy
            if source_path.is_file():
                shutil.copy2(source_path, dest_path)
                action = "copied file"
            elif source_path.is_dir():
                shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                action = "copied directory"
            else:
                return {"success": False, "error": "Source is neither file nor directory"}
            
            # Log operation
            operation = {
                "action": "copy",
                "source": str(source_path),
                "destination": str(dest_path),
                "timestamp": datetime.now().isoformat()
            }
            self.operation_history.append(operation)
            
            return {
                "success": True,
                "source": str(source_path),
                "destination": str(dest_path),
                "action": action,
                "size": source_path.stat().st_size if source_path.is_file() else "directory"
            }
            
        except Exception as e:
            logger.error(f"Error copying file: {e}")
            return {"success": False, "error": str(e)}
    
    async def move_file(self, source: str, destination: str) -> Dict[str, Any]:
        """Move or rename a file."""
        try:
            # Validate source path
            source_validation = self.safety_manager.validate_path(source)
            if not source_validation["safe"]:
                return {"success": False, "error": f"Source: {source_validation['reason']}"}
            
            source_path = Path(source_validation["resolved_path"])
            dest_path = Path(destination).expanduser().resolve()
            
            # Create destination directory if needed
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create backup if destination exists
            if dest_path.exists():
                backup_path = dest_path.with_suffix(dest_path.suffix + ".backup")
                shutil.copy2(dest_path, backup_path)
                logger.info(f"Created backup: {backup_path}")
            
            # Perform move
            shutil.move(str(source_path), str(dest_path))
            
            # Log operation
            operation = {
                "action": "move",
                "source": str(source_path),
                "destination": str(dest_path),
                "timestamp": datetime.now().isoformat()
            }
            self.operation_history.append(operation)
            
            return {
                "success": True,
                "source": str(source_path),
                "destination": str(dest_path),
                "action": "moved"
            }
            
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_file(self, file_path: str, confirm: bool = False) -> Dict[str, Any]:
        """Delete file or directory."""
        try:
            # Validate path
            validation = self.safety_manager.validate_path(file_path)
            if not validation["safe"]:
                return {"success": False, "error": validation["reason"]}
            
            path = Path(validation["resolved_path"])
            
            # Safety check - require confirmation for delete operations
            if not confirm and self.safety_manager.requires_confirmation("delete"):
                return {
                    "success": False,
                    "error": "Delete operation requires confirmation",
                    "requires_confirmation": True,
                    "path": str(path)
                }
            
            # Create backup before deletion
            backup_path = self.temp_manager.temp_root / "backups" / f"{path.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path.parent.mkdir(exist_ok=True)
            
            if path.is_file():
                shutil.copy2(path, backup_path)
                path.unlink()
                action = "deleted file"
            elif path.is_dir():
                shutil.copytree(path, backup_path)
                shutil.rmtree(path)
                action = "deleted directory"
            
            # Log operation
            operation = {
                "action": "delete",
                "path": str(path),
                "backup": str(backup_path),
                "timestamp": datetime.now().isoformat()
            }
            self.operation_history.append(operation)
            
            return {
                "success": True,
                "path": str(path),
                "action": action,
                "backup_location": str(backup_path)
            }
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return {"success": False, "error": str(e)}
    
    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze file properties and content."""
        try:
            # Validate path
            validation = self.safety_manager.validate_path(file_path)
            if not validation["safe"]:
                return {"success": False, "error": validation["reason"]}
            
            path = Path(validation["resolved_path"])
            stat = path.stat()
            
            result = {
                "success": True,
                "path": str(path),
                "name": path.name,
                "size": stat.st_size,
                "size_human": self._format_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "extension": path.suffix.lower(),
                "is_file": path.is_file(),
                "is_directory": path.is_dir(),
                "permissions": oct(stat.st_mode)[-3:]
            }
            
            # Add content analysis for text files
            if path.is_file() and path.suffix.lower() in ['.txt', '.py', '.js', '.html', '.css', '.json', '.yaml', '.yml', '.md']:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read(2000)  # First 2000 characters
                        lines = content.split('\n')
                        result.update({
                            "content_preview": content,
                            "line_count": len(lines),
                            "encoding": "utf-8",
                            "file_type": "text"
                        })
                except Exception as e:
                    result["content_preview"] = f"Could not read file content: {e}"
            
            # Save analysis to temp folder
            analysis_path = self.temp_manager.get_analysis_path(path.stem)
            with open(analysis_path, 'w') as f:
                json.dump(result, f, indent=2)
            
            result["analysis_saved"] = str(analysis_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing file: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_files(self, directory: str, query: str, file_type: str = None) -> Dict[str, Any]:
        """Search for files by name or content."""
        try:
            # Validate path
            validation = self.safety_manager.validate_path(directory)
            if not validation["safe"]:
                return {"success": False, "error": validation["reason"]}
            
            path = Path(validation["resolved_path"])
            matches = []
            
            # Search pattern
            if file_type:
                pattern = f"*.{file_type}"
            else:
                pattern = "*"
            
            for item in path.rglob(pattern):
                if item.is_file():
                    # Check filename match
                    if query.lower() in item.name.lower():
                        matches.append({
                            "path": str(item),
                            "name": item.name,
                            "size": item.stat().st_size,
                            "match_type": "filename"
                        })
                    
                    # Check content match for text files
                    elif item.suffix.lower() in ['.txt', '.py', '.js', '.html', '.css', '.json', '.md']:
                        try:
                            with open(item, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if query.lower() in content.lower():
                                    matches.append({
                                        "path": str(item),
                                        "name": item.name,
                                        "size": item.stat().st_size,
                                        "match_type": "content"
                                    })
                        except:
                            continue
            
            return {
                "success": True,
                "query": query,
                "directory": str(path),
                "matches": matches,
                "total_matches": len(matches)
            }
            
        except Exception as e:
            logger.error(f"Error searching files: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"


class ScreenCapture:
    """Enhanced screen capture and image analysis."""
    
    def __init__(self, temp_manager: TempFileManager):
        self.temp_manager = temp_manager
    
    async def take_screenshot(self, save_path: str = None) -> Dict[str, Any]:
        """Take a screenshot and save to temp folder."""
        try:
            if not SCREENSHOT_AVAILABLE:
                return {"success": False, "error": "Screenshot functionality not available"}
            
            # Take screenshot
            screenshot = ImageGrab.grab()
            
            # Use temp folder if no path specified
            if save_path is None:
                save_path = self.temp_manager.get_screenshot_path()
            else:
                save_path = Path(save_path).expanduser()
            
            # Ensure directory exists
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save screenshot
            screenshot.save(save_path)
            
            return {
                "success": True,
                "path": str(save_path),
                "size": screenshot.size,
                "mode": screenshot.mode,
                "file_size": save_path.stat().st_size,
                "file_size_human": AdvancedFileManager._format_size(save_path.stat().st_size)
            }
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return {"success": False, "error": str(e)}
    
    async def analyze_screenshot(self, screenshot_path: str = None) -> Dict[str, Any]:
        """Analyze screenshot with vision model."""
        try:
            # Take screenshot if path not provided
            if screenshot_path is None:
                screenshot_result = await self.take_screenshot()
                if not screenshot_result.get("success"):
                    return screenshot_result
                screenshot_path = screenshot_result["path"]
            
            # Analyze with vision model
            logger.info(f"Analyzing screenshot with vision model: {screenshot_path}")
            
            enhanced_prompt = """Analyze this screenshot and provide a detailed description of what you see. Be accurate and only describe what is actually visible.

Please describe:
1. Applications and windows that are open
2. Text content that is clearly readable
3. UI elements like buttons, menus, toolbars
4. File names, folder contents, or documents visible
5. Overall layout and what the user appears to be doing

Be factual and precise. If something is unclear or partially obscured, mention that rather than guessing."""

            analysis_result = ai_engine.process_image_input(
                screenshot_path,
                enhanced_prompt
            )
            
            if analysis_result.get("error"):
                return {
                    "success": False,
                    "error": f"Image analysis failed: {analysis_result['error']}",
                    "screenshot_path": screenshot_path
                }
            
            return {
                "success": True,
                "screenshot_path": screenshot_path,
                "analysis": analysis_result["response"],
                "processing_time_ms": analysis_result.get("processing_time_ms", 0),
                "model_used": analysis_result.get("model_used", "llava:latest")
            }
            
        except Exception as e:
            logger.error(f"Error analyzing screenshot: {e}")
            return {"success": False, "error": str(e)}


class WebSearch:
    """Web search functionality."""
    
    @staticmethod
    async def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web for information."""
        try:
            if not config.is_online_mode():
                return {"success": False, "error": "Online mode is disabled"}
            
            if not REQUESTS_AVAILABLE:
                return {"success": False, "error": "Web search functionality not available"}
            
            # Use DuckDuckGo Instant Answer API
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            result = {
                "success": True,
                "query": query,
                "abstract": data.get("Abstract", ""),
                "abstract_source": data.get("AbstractSource", ""),
                "abstract_url": data.get("AbstractURL", ""),
                "answer": data.get("Answer", ""),
                "answer_type": data.get("AnswerType", ""),
                "definition": data.get("Definition", ""),
                "definition_source": data.get("DefinitionSource", ""),
                "definition_url": data.get("DefinitionURL", ""),
                "related_topics": []
            }
            
            # Add related topics
            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    result["related_topics"].append({
                        "text": topic.get("Text", ""),
                        "url": topic.get("FirstURL", "")
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return {"success": False, "error": str(e)}


class SystemInfo:
    """System information and monitoring."""
    
    @staticmethod
    async def get_system_info() -> Dict[str, Any]:
        """Get system information."""
        try:
            # CPU information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory information
            memory = psutil.virtual_memory()
            
            # Disk information
            disk = psutil.disk_usage('/')
            
            # Network information
            network = psutil.net_io_counters()
            
            return {
                "success": True,
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": cpu_count,
                    "frequency_mhz": cpu_freq.current if cpu_freq else None
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "percent": round((disk.used / disk.total) * 100, 1)
                },
                "network": {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {"success": False, "error": str(e)}


class ActionDispatcher:
    """Enhanced action dispatcher with comprehensive file management."""
    
    def __init__(self):
        # Initialize managers
        self.temp_manager = TempFileManager()
        self.safety_manager = SafetyManager()
        self.file_manager = AdvancedFileManager(self.temp_manager, self.safety_manager)
        self.screen_capture = ScreenCapture(self.temp_manager)
        self.web_search = WebSearch()
        self.system_info = SystemInfo()
        
        # Enhanced action patterns with better matching
        self.action_patterns = {
            # File listing operations - comprehensive patterns
            r"(?:list|show|display)\s+(?:files?|contents?)\s+(?:in\s+|on\s+|at\s+)?(.+)": self._handle_list_files,
            r"(?:what|which)\s+(?:files?|contents?)\s+(?:are\s+)?(?:in\s+|on\s+|at\s+)?(?:my\s+)?(.+)": self._handle_list_files,
            r"(?:show\s+me\s+)?(?:the\s+)?(?:files?|contents?)\s+(?:in\s+|on\s+|of\s+)?(?:my\s+)?(.+)": self._handle_list_files,
            r"(?:browse|explore|look\s+in|check)\s+(?:the\s+)?(.+)(?:\s+(?:folder|directory))?": self._handle_list_files,
            
            # File operations
            r"(?:copy|duplicate|backup)\s+(.+?)\s+(?:to|into)\s+(.+)": self._handle_copy_file,
            r"(?:move|relocate|transfer)\s+(.+?)\s+(?:to|into)\s+(.+)": self._handle_move_file,
            r"(?:delete|remove|trash)\s+(?:the\s+)?(.+)": self._handle_delete_file,
            r"(?:analyze|examine|inspect|check)\s+(?:the\s+)?(?:file\s+)?(.+)": self._handle_analyze_file,
            r"(?:search|find)\s+(?:for\s+)?(.+?)\s+(?:in\s+|on\s+)(.+)": self._handle_search_files,
            
            # Screen capture and analysis - FIXED PATTERNS
            r"(?:take\s+)?(?:a\s+)?screenshot": self._handle_screenshot,
            r"(?:capture\s+)?(?:the\s+)?screen": self._handle_screenshot,
            r"analyze\s+(?:my\s+)?screen": self._handle_analyze_screenshot,
            r"(?:describe|analyze|what'?s\s+(?:in|on))\s+(?:the\s+)?(?:screenshot|image|screen)": self._handle_analyze_screenshot,
            r"(?:what\s+do\s+you\s+see|tell\s+me\s+about\s+the\s+screen)": self._handle_analyze_screenshot,
            r"what\s+am\s+i\s+looking\s+at": self._handle_analyze_screenshot,
            r"what'?s\s+on\s+my\s+screen": self._handle_analyze_screenshot,
            
            # Temp file management
            r"(?:clean|cleanup|clear)\s+(?:temp|temporary)\s+(?:files?|folder)": self._handle_cleanup_temp,
            r"(?:show|list)\s+(?:temp|temporary)\s+(?:files?|folder)": self._handle_show_temp,
            r"temp\s+(?:info|information|status)": self._handle_temp_info,
            
            # Web search
            r"(?:search|look\s+up|find)\s+(?:for\s+)?(.+)": self._handle_web_search,
            r"(?:what\s+is|tell\s+me\s+about)\s+(.+)": self._handle_web_search,
            
            # System info
            r"(?:system\s+)?(?:info|information|status)": self._handle_system_info,
            r"(?:how\s+is\s+)?(?:the\s+)?(?:system|computer)\s+(?:doing|performing)": self._handle_system_info,
        }
    
    async def process_input(self, user_input: str) -> Dict[str, Any]:
        """Process user input and determine if action is needed."""
        try:
            user_input_lower = user_input.lower().strip()
            logger.info(f"Processing input: '{user_input_lower}'")
            
            # Check each pattern in order
            for pattern, handler in self.action_patterns.items():
                match = re.search(pattern, user_input_lower)
                if match:
                    logger.info(f"Action detected - Pattern: {pattern}")
                    logger.info(f"Handler: {handler.__name__}")
                    
                    with log_performance(logger, f"Action execution: {handler.__name__}"):
                        result = await handler(match, user_input)
                    
                    if result.get("success"):
                        return {
                            "action_taken": handler.__name__.replace("_handle_", ""),
                            "success": True,
                            "result": result
                        }
                    else:
                        return {
                            "action_taken": handler.__name__.replace("_handle_", ""),
                            "success": False,
                            "error": result.get("error", "Unknown error")
                        }
            
            # No action pattern matched
            logger.info("No action pattern matched")
            return {"action_taken": None, "success": True}
            
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return {
                "action_taken": None,
                "success": False,
                "error": str(e)
            }
    
    # File operation handlers
    async def _handle_list_files(self, match, original_input: str) -> Dict[str, Any]:
        """Handle file listing request."""
        try:
            directory = match.group(1).strip()
            
            # Handle common directory references
            directory_map = {
                "here": ".",
                "current": ".",
                "this": ".",
                "home": "~",
                "desktop": "~/Desktop",
                "documents": "~/Documents", 
                "downloads": "~/Downloads",
                "pictures": "~/Pictures",
                "videos": "~/Videos",
                "music": "~/Music"
            }
            
            directory = directory_map.get(directory, directory)
            
            # Check for recursive flag
            recursive = "recursive" in original_input.lower() or "all" in original_input.lower()
            
            return await self.file_manager.list_files(directory, recursive=recursive)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_copy_file(self, match, original_input: str) -> Dict[str, Any]:
        """Handle file copy request."""
        try:
            source = match.group(1).strip()
            destination = match.group(2).strip()
            
            return await self.file_manager.copy_file(source, destination)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_move_file(self, match, original_input: str) -> Dict[str, Any]:
        """Handle file move/rename request."""
        try:
            source = match.group(1).strip()
            destination = match.group(2).strip()
            
            return await self.file_manager.move_file(source, destination)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_delete_file(self, match, original_input: str) -> Dict[str, Any]:
        """Handle file deletion request."""
        try:
            file_path = match.group(1).strip()
            
            # Check for confirmation in input
            confirm = "confirm" in original_input.lower() or "yes" in original_input.lower()
            
            return await self.file_manager.delete_file(file_path, confirm=confirm)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_analyze_file(self, match, original_input: str) -> Dict[str, Any]:
        """Handle file analysis request."""
        try:
            file_path = match.group(1).strip()
            
            return await self.file_manager.analyze_file(file_path)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_search_files(self, match, original_input: str) -> Dict[str, Any]:
        """Handle file search request."""
        try:
            query = match.group(1).strip()
            directory = match.group(2).strip()
            
            # Handle common directory references
            directory_map = {
                "here": ".",
                "current": ".",
                "this": ".",
                "home": "~",
                "desktop": "~/Desktop",
                "documents": "~/Documents", 
                "downloads": "~/Downloads"
            }
            
            directory = directory_map.get(directory, directory)
            
            return await self.file_manager.search_files(directory, query)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Screen capture handlers
    async def _handle_screenshot(self, match, original_input: str) -> Dict[str, Any]:
        """Handle screenshot request."""
        try:
            return await self.screen_capture.take_screenshot()
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_analyze_screenshot(self, match, original_input: str) -> Dict[str, Any]:
        """Handle screenshot analysis request."""
        try:
            return await self.screen_capture.analyze_screenshot()
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Temp file handlers
    async def _handle_cleanup_temp(self, match, original_input: str) -> Dict[str, Any]:
        """Handle temp file cleanup request."""
        try:
            return self.temp_manager.cleanup_old_files()
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_show_temp(self, match, original_input: str) -> Dict[str, Any]:
        """Handle show temp files request."""
        try:
            return self.temp_manager.get_temp_info()
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_temp_info(self, match, original_input: str) -> Dict[str, Any]:
        """Handle temp info request."""
        try:
            return self.temp_manager.get_temp_info()
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # Web search handler
    async def _handle_web_search(self, match, original_input: str) -> Dict[str, Any]:
        """Handle web search request."""
        try:
            query = match.group(1).strip()
            
            return await self.web_search.search_web(query)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # System info handler
    async def _handle_system_info(self, match, original_input: str) -> Dict[str, Any]:
        """Handle system info request."""
        try:
            return await self.system_info.get_system_info()
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_available_actions(self) -> List[Dict[str, str]]:
        """Get list of available actions."""
        return [
            {
                "category": "File Management",
                "actions": [
                    "List files in directory",
                    "Copy files/directories",
                    "Move/rename files",
                    "Delete files (with backup)",
                    "Analyze file properties",
                    "Search files by name/content"
                ]
            },
            {
                "category": "Screen Capture & Analysis",
                "actions": [
                    "Take screenshot",
                    "Analyze screen content"
                ]
            },
            {
                "category": "Temporary File Management",
                "actions": [
                    "Clean up temp files",
                    "Show temp folder info",
                    "Manage temp storage"
                ]
            },
            {
                "category": "Web Search",
                "actions": [
                    "Search the web",
                    "Look up information"
                ]
            },
            {
                "category": "System Information",
                "actions": [
                    "Get system status",
                    "Check performance metrics"
                ]
            }
        ]


# Test function
async def test_action_dispatcher():
    """Test the enhanced action dispatcher."""
    dispatcher = ActionDispatcher()
    
    test_inputs = [
        "analyze my screen",
        "list files on desktop",
        "what files are in my documents",
        "take a screenshot",
        "temp info",
        "system info"
    ]
    
    for test_input in test_inputs:
        print(f"\nTesting: {test_input}")
        result = await dispatcher.process_input(test_input)
        print(f"Result: {result}")


if __name__ == "__main__":
    asyncio.run(test_action_dispatcher())
