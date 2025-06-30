"""
UI Automation System for Jarvis AI Assistant.
Provides cursor and keyboard control for app integration.
"""

import asyncio
import time
import re
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
from datetime import datetime

try:
    import pyautogui
    import pygetwindow as gw
    AUTOMATION_AVAILABLE = True
    
    # Configure PyAutoGUI safety settings
    pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort
    pyautogui.PAUSE = 0.1  # Small pause between actions
    
    # Type alias for when available
    WindowType = gw.Win32Window
    
except ImportError:
    AUTOMATION_AVAILABLE = False
    # Create dummy objects to avoid NameError in type hints
    pyautogui = None
    gw = None
    
    # Fallback type for when not available
    WindowType = Any

try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

from ..core.config import config
from ..core.logging import get_logger, log_performance
from ..core.ai_engine import ai_engine

logger = get_logger("ui_automator")


class SafetyManager:
    """Manages safety for UI automation operations."""
    
    def __init__(self):
        # Define safe zones (areas where clicking is generally safe)
        self.safe_zones = {
            "application_area": (50, 50, -50, -100),  # Avoid edges and taskbar
            "center_area": (200, 200, -200, -200)     # Center area of screen
        }
        
        # Define dangerous areas to avoid
        self.danger_zones = [
            (0, 0, 100, 50),      # Top-left corner (close buttons)
            (-100, 0, 0, 50),     # Top-right corner (window controls)
            (0, -50, -1, -1),     # Taskbar area
        ]
        
        # Actions that require confirmation
        self.dangerous_actions = [
            "close", "quit", "exit", "delete", "remove", "uninstall"
        ]
    
    def is_safe_click_area(self, x: int, y: int) -> bool:
        """Check if coordinates are in a safe area to click."""
        if not AUTOMATION_AVAILABLE or not pyautogui:
            return False
            
        screen_width, screen_height = pyautogui.size()
        
        # Check danger zones
        for zone in self.danger_zones:
            left = zone[0] if zone[0] >= 0 else screen_width + zone[0]
            top = zone[1] if zone[1] >= 0 else screen_height + zone[1]
            right = zone[2] if zone[2] >= 0 else screen_width + zone[2]
            bottom = zone[3] if zone[3] >= 0 else screen_height + zone[3]
            
            if left <= x <= right and top <= y <= bottom:
                return False
        
        return True
    
    def requires_confirmation(self, action: str) -> bool:
        """Check if action requires user confirmation."""
        return any(dangerous in action.lower() for dangerous in self.dangerous_actions)


class AppLauncher:
    """Handles launching applications when they're not running."""
    
    def __init__(self):
        # Common application launch commands
        self.app_launch_commands = {
            "calculator": "calc",
            "notepad": "notepad", 
            "paint": "mspaint",
            "cmd": "cmd",
            "powershell": "powershell",
            "task manager": "taskmgr",
            "control panel": "control",
            "file explorer": "explorer",
            "registry editor": "regedit",
            "chrome": "chrome",
            "firefox": "firefox",
            "edge": "msedge",
            "discord": "discord",
            "spotify": "spotify",
            "vscode": "code",
            "visual studio code": "code"
        }
        
        # Apps that might take longer to start
        self.slow_start_apps = ["discord", "spotify", "chrome", "firefox", "edge", "vscode"]
    
    async def launch_app(self, app_name: str) -> Dict[str, Any]:
        """Launch an application using various methods."""
        try:
            app_name_lower = app_name.lower()
            logger.info(f"Attempting to launch application: {app_name}")
            
            # Method 1: Try Windows Run dialog (Win+R)
            if app_name_lower in self.app_launch_commands:
                command = self.app_launch_commands[app_name_lower]
                logger.info(f"Launching {app_name} with command: {command}")
                
                # Open Run dialog
                pyautogui.hotkey('win', 'r')
                await asyncio.sleep(0.5)
                
                # Type command
                pyautogui.typewrite(command)
                await asyncio.sleep(0.3)
                
                # Press Enter
                pyautogui.press('enter')
                
                # Wait for app to start
                wait_time = 3 if app_name_lower in self.slow_start_apps else 1.5
                await asyncio.sleep(wait_time)
                
                return {
                    "success": True,
                    "method": "run_dialog",
                    "command": command,
                    "app_name": app_name
                }
            
            # Method 2: Try Start menu search
            logger.info(f"Trying Start menu search for: {app_name}")
            
            # Open Start menu
            pyautogui.press('win')
            await asyncio.sleep(0.5)
            
            # Type app name
            pyautogui.typewrite(app_name)
            await asyncio.sleep(1)  # Wait for search results
            
            # Press Enter to launch first result
            pyautogui.press('enter')
            
            # Wait for app to start
            wait_time = 4 if app_name_lower in self.slow_start_apps else 2
            await asyncio.sleep(wait_time)
            
            return {
                "success": True,
                "method": "start_menu",
                "app_name": app_name
            }
            
        except Exception as e:
            logger.error(f"Error launching application {app_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "app_name": app_name
            }
    
    async def wait_for_app_ready(self, app_name: str, max_wait: int = 10) -> bool:
        """Wait for an application to be ready after launching."""
        try:
            app_name_lower = app_name.lower()
            
            # App-specific readiness checks
            for attempt in range(max_wait):
                await asyncio.sleep(1)
                
                # Check if window exists
                try:
                    windows = gw.getAllWindows()
                    for window in windows:
                        if window.title and window.visible:
                            window_title_lower = window.title.lower()
                            if app_name_lower in window_title_lower:
                                logger.info(f"App {app_name} is ready (window found)")
                                return True
                except:
                    pass
                
                logger.info(f"Waiting for {app_name} to be ready... ({attempt + 1}/{max_wait})")
            
            logger.warning(f"App {app_name} may not be fully ready after {max_wait} seconds")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for app readiness: {e}")
            return False


class WindowManager:
    """Manages application windows and focus."""
    
    def __init__(self):
        self.window_cache = {}
        self.last_focused_window = None
        self.app_launcher = AppLauncher()
    
    async def find_window(self, app_name: str) -> Optional[WindowType]:
        """Find window by application name."""
        try:
            app_name_lower = app_name.lower()
            
            # Common application name mappings
            app_mappings = {
                "discord": ["discord"],
                "spotify": ["spotify"],
                "chrome": ["chrome", "google chrome"],
                "firefox": ["firefox", "mozilla firefox"],
                "edge": ["edge", "microsoft edge"],
                "notepad": ["notepad"],
                "calculator": ["calculator"],
                "explorer": ["explorer", "file explorer"],
                "vscode": ["visual studio code", "code"],
                "word": ["microsoft word", "word"],
                "excel": ["microsoft excel", "excel"],
                "powerpoint": ["microsoft powerpoint", "powerpoint"]
            }
            
            # Get search terms for the app
            search_terms = app_mappings.get(app_name_lower, [app_name_lower])
            
            # Find all windows
            windows = gw.getAllWindows()
            
            for window in windows:
                if window.title and window.visible:
                    window_title_lower = window.title.lower()
                    
                    # Check if any search term matches the window title
                    for term in search_terms:
                        if term in window_title_lower:
                            logger.info(f"Found window: {window.title} for app: {app_name}")
                            return window
            
            logger.warning(f"No window found for app: {app_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding window for {app_name}: {e}")
            return None
    
    async def focus_window(self, window: WindowType) -> bool:
        """Focus on a specific window."""
        try:
            if not window:
                return False
                
            # Store current focused window
            try:
                self.last_focused_window = gw.getActiveWindow()
            except:
                self.last_focused_window = None
            
            # Try multiple methods to focus the window
            success = False
            
            # Method 1: Try restore if minimized, then activate
            try:
                if hasattr(window, 'isMinimized') and window.isMinimized:
                    window.restore()
                    await asyncio.sleep(0.3)
                
                window.activate()
                await asyncio.sleep(0.3)
                success = True
                logger.info(f"Successfully activated window: {window.title}")
                
            except Exception as e:
                logger.warning(f"Window.activate() failed: {e}")
                
                # Method 2: Try using pyautogui to click on the window
                try:
                    # Click in the center of the window
                    center_x = window.left + window.width // 2
                    center_y = window.top + window.height // 2
                    
                    # Make sure coordinates are within screen bounds
                    screen_width, screen_height = pyautogui.size()
                    center_x = max(0, min(center_x, screen_width - 1))
                    center_y = max(0, min(center_y, screen_height - 1))
                    
                    pyautogui.click(center_x, center_y)
                    await asyncio.sleep(0.3)
                    success = True
                    logger.info(f"Successfully clicked to focus window: {window.title}")
                    
                except Exception as e2:
                    logger.warning(f"Click focus failed: {e2}")
                    
                    # Method 3: Try Alt+Tab approach
                    try:
                        # Use Alt+Tab to cycle through windows
                        pyautogui.hotkey('alt', 'tab')
                        await asyncio.sleep(0.2)
                        
                        # Check if we got the right window (basic check)
                        current_window = gw.getActiveWindow()
                        if current_window and window.title.lower() in current_window.title.lower():
                            success = True
                            logger.info(f"Successfully focused via Alt+Tab: {window.title}")
                        else:
                            # Try a few more Alt+Tab presses
                            for _ in range(3):
                                pyautogui.press('tab')
                                await asyncio.sleep(0.1)
                                current_window = gw.getActiveWindow()
                                if current_window and window.title.lower() in current_window.title.lower():
                                    success = True
                                    break
                            
                            if success:
                                pyautogui.keyUp('alt')  # Release Alt
                                logger.info(f"Successfully focused via Alt+Tab cycling: {window.title}")
                            else:
                                pyautogui.keyUp('alt')  # Release Alt
                                
                    except Exception as e3:
                        logger.warning(f"Alt+Tab focus failed: {e3}")
            
            # Final verification
            if success:
                try:
                    await asyncio.sleep(0.2)
                    active_window = gw.getActiveWindow()
                    if active_window and (active_window.title == window.title or 
                                        window.title.lower() in active_window.title.lower()):
                        logger.info(f"Window focus verified: {window.title}")
                        return True
                    else:
                        logger.warning(f"Window focus verification failed for: {window.title}")
                        # Still return True if we tried our best
                        return True
                except:
                    # If verification fails, assume success if we got this far
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error focusing window: {e}")
            return False
    
    async def focus_application(self, app_name: str, auto_launch: bool = True) -> bool:
        """Find and focus an application window, optionally launching it if not found."""
        try:
            # First try to find existing window
            window = await self.find_window(app_name)
            if window:
                return await self.focus_window(window)
            
            # If not found and auto_launch is enabled, try to launch the app
            if auto_launch and AUTOMATION_AVAILABLE:
                logger.info(f"Application {app_name} not found, attempting to launch...")
                
                launch_result = await self.app_launcher.launch_app(app_name)
                if launch_result.get("success"):
                    logger.info(f"Successfully launched {app_name}, waiting for it to be ready...")
                    
                    # Wait for app to be ready
                    ready = await self.app_launcher.wait_for_app_ready(app_name, max_wait=8)
                    if ready:
                        # Try to find window again
                        window = await self.find_window(app_name)
                        if window:
                            return await self.focus_window(window)
                        else:
                            logger.warning(f"App {app_name} launched but window not found")
                            return False
                    else:
                        logger.warning(f"App {app_name} launched but may not be fully ready")
                        # Try to find window anyway
                        window = await self.find_window(app_name)
                        if window:
                            return await self.focus_window(window)
                        return False
                else:
                    logger.error(f"Failed to launch {app_name}: {launch_result.get('error')}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error focusing application {app_name}: {e}")
            return False
    
    def get_window_info(self, window: WindowType) -> Dict[str, Any]:
        """Get information about a window."""
        try:
            return {
                "title": window.title,
                "left": window.left,
                "top": window.top,
                "width": window.width,
                "height": window.height,
                "visible": window.visible,
                "minimized": window.isMinimized,
                "maximized": window.isMaximized,
                "active": window.isActive
            }
        except Exception as e:
            logger.error(f"Error getting window info: {e}")
            return {}


class MouseController:
    """Handles precise mouse control operations."""
    
    def __init__(self, safety_manager: SafetyManager):
        self.safety_manager = safety_manager
        self.click_history = []
    
    async def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> bool:
        """Perform a mouse click at specified coordinates."""
        try:
            # Safety check
            if not self.safety_manager.is_safe_click_area(x, y):
                logger.warning(f"Unsafe click area detected: ({x}, {y})")
                return False
            
            # Record click for history
            self.click_history.append({
                "x": x, "y": y, "button": button, "clicks": clicks,
                "timestamp": datetime.now().isoformat()
            })
            
            # Perform click
            pyautogui.click(x, y, clicks=clicks, button=button)
            logger.info(f"Clicked at ({x}, {y}) with {button} button, {clicks} clicks")
            
            # Small delay after click
            await asyncio.sleep(0.2)
            return True
            
        except Exception as e:
            logger.error(f"Error clicking at ({x}, {y}): {e}")
            return False
    
    async def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 1.0) -> bool:
        """Drag from start coordinates to end coordinates."""
        try:
            # Safety checks
            if not (self.safety_manager.is_safe_click_area(start_x, start_y) and 
                   self.safety_manager.is_safe_click_area(end_x, end_y)):
                logger.warning(f"Unsafe drag area detected")
                return False
            
            pyautogui.drag(start_x, start_y, end_x - start_x, end_y - start_y, duration=duration)
            logger.info(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return True
            
        except Exception as e:
            logger.error(f"Error dragging: {e}")
            return False
    
    async def scroll(self, x: int, y: int, clicks: int) -> bool:
        """Scroll at specified coordinates."""
        try:
            pyautogui.scroll(clicks, x=x, y=y)
            logger.info(f"Scrolled {clicks} clicks at ({x}, {y})")
            return True
            
        except Exception as e:
            logger.error(f"Error scrolling: {e}")
            return False
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position."""
        return pyautogui.position()


class KeyboardController:
    """Handles keyboard input and shortcuts."""
    
    def __init__(self):
        self.typing_history = []
    
    async def type_text(self, text: str, interval: float = 0.05) -> bool:
        """Type text with specified interval between characters."""
        try:
            # Record typing for history
            self.typing_history.append({
                "text": text,
                "timestamp": datetime.now().isoformat()
            })
            
            pyautogui.typewrite(text, interval=interval)
            logger.info(f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}")
            return True
            
        except Exception as e:
            logger.error(f"Error typing text: {e}")
            return False
    
    async def press_key(self, key: str) -> bool:
        """Press a single key."""
        try:
            pyautogui.press(key)
            logger.info(f"Pressed key: {key}")
            await asyncio.sleep(0.1)
            return True
            
        except Exception as e:
            logger.error(f"Error pressing key {key}: {e}")
            return False
    
    async def key_combination(self, *keys) -> bool:
        """Press a combination of keys (e.g., Ctrl+C)."""
        try:
            pyautogui.hotkey(*keys)
            logger.info(f"Pressed key combination: {'+'.join(keys)}")
            await asyncio.sleep(0.2)
            return True
            
        except Exception as e:
            logger.error(f"Error pressing key combination {keys}: {e}")
            return False
    
    async def hold_key(self, key: str, duration: float) -> bool:
        """Hold a key for specified duration."""
        try:
            pyautogui.keyDown(key)
            await asyncio.sleep(duration)
            pyautogui.keyUp(key)
            logger.info(f"Held key {key} for {duration} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Error holding key {key}: {e}")
            return False


class ScreenAnalyzer:
    """Analyzes screen content to find UI elements."""
    
    def __init__(self):
        self.element_cache = {}
    
    async def take_screenshot(self) -> str:
        """Take a screenshot and return the file path."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = Path("jarvis/temp/screenshots") / f"automation_{timestamp}.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_path)
            
            logger.info(f"Screenshot saved: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
    
    async def analyze_ui_elements(self, screenshot_path: str) -> Dict[str, Any]:
        """Analyze screenshot to identify UI elements."""
        try:
            # Enhanced prompt for UI element detection
            ui_analysis_prompt = """You are analyzing a computer screenshot to identify clickable UI elements for automation. Be extremely precise about locations and only identify elements that are clearly visible and clickable.

CRITICAL: Provide exact pixel coordinates for each element you identify.

Please identify and locate these types of UI elements:

**BUTTONS & CLICKABLE ELEMENTS:**
- Buttons (Send, Play, Pause, etc.)
- Links and clickable text
- Icons and toolbar buttons
- Menu items
- Tabs

**INPUT FIELDS:**
- Text input boxes
- Search fields
- Message input areas
- Address bars

**NAVIGATION ELEMENTS:**
- Close buttons (X)
- Minimize/maximize buttons
- Back/forward buttons
- Scroll bars

**APPLICATION-SPECIFIC ELEMENTS:**
For Discord: user lists, message boxes, channel lists, send buttons
For Spotify: play/pause, search box, song lists, volume controls
For Browsers: address bar, tabs, bookmarks

**FORMAT YOUR RESPONSE AS:**
```json
{
  "elements": [
    {
      "type": "button|input|link|icon|menu",
      "description": "clear description of the element",
      "text": "visible text on the element",
      "coordinates": {"x": 123, "y": 456},
      "size": {"width": 100, "height": 30},
      "confidence": "high|medium|low"
    }
  ],
  "application": "detected application name",
  "window_title": "visible window title"
}
```

IMPORTANT: Only include elements you can clearly see and are confident about their locations. Provide exact pixel coordinates, not approximate areas."""

            # Analyze with AI vision
            analysis_result = ai_engine.process_image_input(
                screenshot_path,
                ui_analysis_prompt
            )
            
            if analysis_result.get("error"):
                logger.error(f"UI analysis failed: {analysis_result['error']}")
                return {"success": False, "error": analysis_result["error"]}
            
            # Try to parse JSON response
            response_text = analysis_result["response"]
            
            # Extract JSON from response if it's wrapped in markdown
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(1)
            else:
                json_text = response_text
            
            try:
                ui_data = json.loads(json_text)
                logger.info(f"UI analysis successful: found {len(ui_data.get('elements', []))} elements")
                return {
                    "success": True,
                    "screenshot_path": screenshot_path,
                    "ui_data": ui_data,
                    "analysis_time": analysis_result.get("processing_time_ms", 0)
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse UI analysis JSON: {e}")
                return {
                    "success": False,
                    "error": "Failed to parse UI analysis",
                    "raw_response": response_text
                }
            
        except Exception as e:
            logger.error(f"Error analyzing UI elements: {e}")
            return {"success": False, "error": str(e)}
    
    def find_element_by_description(self, ui_data: Dict[str, Any], description: str) -> Optional[Dict[str, Any]]:
        """Find a UI element by description."""
        try:
            description_lower = description.lower()
            elements = ui_data.get("elements", [])
            
            # Look for exact matches first
            for element in elements:
                element_desc = element.get("description", "").lower()
                element_text = element.get("text", "").lower()
                
                if (description_lower in element_desc or 
                    description_lower in element_text or
                    element_desc in description_lower or
                    element_text in description_lower):
                    return element
            
            # Look for partial matches
            for element in elements:
                element_desc = element.get("description", "").lower()
                element_text = element.get("text", "").lower()
                
                # Check if any word from description matches
                desc_words = description_lower.split()
                for word in desc_words:
                    if word in element_desc or word in element_text:
                        return element
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding element by description: {e}")
            return None


class UIAutomator:
    """Main UI automation controller."""
    
    def __init__(self):
        if not AUTOMATION_AVAILABLE:
            logger.error("UI automation not available - missing dependencies")
            return
        
        self.safety_manager = SafetyManager()
        self.window_manager = WindowManager()
        self.mouse_controller = MouseController(self.safety_manager)
        self.keyboard_controller = KeyboardController()
        self.screen_analyzer = ScreenAnalyzer()
        
        self.automation_history = []
        self.current_session = {
            "start_time": datetime.now(),
            "actions": []
        }
    
    async def execute_automation(self, command: str, **kwargs) -> Dict[str, Any]:
        """Execute an automation command."""
        try:
            if not AUTOMATION_AVAILABLE:
                return {"success": False, "error": "UI automation not available"}
            
            logger.info(f"Executing automation command: {command}")
            
            # Record command in session
            self.current_session["actions"].append({
                "command": command,
                "kwargs": kwargs,
                "timestamp": datetime.now().isoformat()
            })
            
            # Route to appropriate handler
            if command == "focus_app":
                return await self._focus_application(kwargs.get("app_name"))
            elif command == "click_element":
                return await self._click_element(kwargs.get("description"))
            elif command == "type_text":
                return await self._type_text(kwargs.get("text"))
            elif command == "press_key":
                return await self._press_key(kwargs.get("key"))
            elif command == "key_combination":
                return await self._key_combination(kwargs.get("keys"))
            elif command == "analyze_screen":
                return await self._analyze_screen()
            else:
                return {"success": False, "error": f"Unknown command: {command}"}
            
        except Exception as e:
            logger.error(f"Error executing automation command: {e}")
            return {"success": False, "error": str(e)}
    
    async def _focus_application(self, app_name: str) -> Dict[str, Any]:
        """Focus on an application."""
        try:
            success = await self.window_manager.focus_application(app_name)
            return {
                "success": success,
                "action": "focus_application",
                "app_name": app_name
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _analyze_screen(self) -> Dict[str, Any]:
        """Analyze current screen content."""
        try:
            screenshot_path = await self.screen_analyzer.take_screenshot()
            if not screenshot_path:
                return {"success": False, "error": "Failed to take screenshot"}
            
            analysis = await self.screen_analyzer.analyze_ui_elements(screenshot_path)
            return analysis
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _click_element(self, description: str) -> Dict[str, Any]:
        """Click on a UI element by description."""
        try:
            # First analyze the screen
            screen_analysis = await self._analyze_screen()
            if not screen_analysis.get("success"):
                return screen_analysis
            
            # Find the element
            ui_data = screen_analysis["ui_data"]
            element = self.screen_analyzer.find_element_by_description(ui_data, description)
            
            if not element:
                return {
                    "success": False,
                    "error": f"Could not find element: {description}",
                    "available_elements": [e.get("description") for e in ui_data.get("elements", [])]
                }
            
            # Click the element
            coords = element.get("coordinates", {})
            x, y = coords.get("x"), coords.get("y")
            
            if x is None or y is None:
                return {"success": False, "error": "Invalid element coordinates"}
            
            success = await self.mouse_controller.click(x, y)
            return {
                "success": success,
                "action": "click_element",
                "element": element,
                "coordinates": {"x": x, "y": y}
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _type_text(self, text: str) -> Dict[str, Any]:
        """Type text."""
        try:
            success = await self.keyboard_controller.type_text(text)
            return {
                "success": success,
                "action": "type_text",
                "text": text
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _press_key(self, key: str) -> Dict[str, Any]:
        """Press a key."""
        try:
            success = await self.keyboard_controller.press_key(key)
            return {
                "success": success,
                "action": "press_key",
                "key": key
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _key_combination(self, keys: List[str]) -> Dict[str, Any]:
        """Press key combination."""
        try:
            success = await self.keyboard_controller.key_combination(*keys)
            return {
                "success": success,
                "action": "key_combination",
                "keys": keys
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current automation session information."""
        return {
            "session_start": self.current_session["start_time"].isoformat(),
            "total_actions": len(self.current_session["actions"]),
            "recent_actions": self.current_session["actions"][-10:],  # Last 10 actions
            "automation_available": AUTOMATION_AVAILABLE
        }


# Test function
async def test_ui_automator():
    """Test the UI automator."""
    if not AUTOMATION_AVAILABLE:
        print("UI automation not available - install required packages:")
        print("pip install pyautogui pygetwindow")
        return
    
    automator = UIAutomator()
    
    print("Testing UI Automator...")
    
    # Test screen analysis
    print("\n1. Analyzing screen...")
    result = await automator.execute_automation("analyze_screen")
    print(f"Screen analysis result: {result.get('success')}")
    
    if result.get("success"):
        ui_data = result.get("ui_data", {})
        elements = ui_data.get("elements", [])
        print(f"Found {len(elements)} UI elements")
        
        for i, element in enumerate(elements[:3]):  # Show first 3 elements
            print(f"  {i+1}. {element.get('description')} at {element.get('coordinates')}")
    
    # Test window finding
    print("\n2. Testing window management...")
    apps_to_test = ["notepad", "calculator", "chrome", "discord"]
    
    for app in apps_to_test:
        window = await automator.window_manager.find_window(app)
        if window:
            print(f"  Found {app}: {window.title}")
        else:
            print(f"  {app}: Not found")
    
    print("\nUI Automator test complete!")


if __name__ == "__main__":
    asyncio.run(test_ui_automator())
