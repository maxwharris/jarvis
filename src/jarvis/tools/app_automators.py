"""
App-specific automation handlers for popular applications.
Provides specialized automation workflows for Discord, Spotify, browsers, etc.
"""

import asyncio
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from .ui_automator import UIAutomator
from ..core.logging import get_logger

logger = get_logger("app_automators")


class DiscordAutomator:
    """Specialized automation for Discord."""
    
    def __init__(self, ui_automator: UIAutomator):
        self.ui_automator = ui_automator
        self.app_name = "discord"
    
    async def send_message(self, recipient: str, message: str) -> Dict[str, Any]:
        """Send a message to a user on Discord."""
        try:
            logger.info(f"Sending Discord message to {recipient}: {message}")
            
            # Step 1: Focus Discord
            focus_result = await self.ui_automator.execute_automation("focus_app", app_name=self.app_name)
            if not focus_result.get("success"):
                return {"success": False, "error": "Could not focus Discord"}
            
            await asyncio.sleep(1)  # Wait for Discord to be ready
            
            # Step 2: Open DM search (Ctrl+K)
            search_result = await self.ui_automator.execute_automation("key_combination", keys=["ctrl", "k"])
            if not search_result.get("success"):
                return {"success": False, "error": "Could not open Discord search"}
            
            await asyncio.sleep(0.5)
            
            # Step 3: Type recipient name
            type_result = await self.ui_automator.execute_automation("type_text", text=recipient)
            if not type_result.get("success"):
                return {"success": False, "error": "Could not type recipient name"}
            
            await asyncio.sleep(1)  # Wait for search results
            
            # Step 4: Press Enter to select first result
            enter_result = await self.ui_automator.execute_automation("press_key", key="enter")
            if not enter_result.get("success"):
                return {"success": False, "error": "Could not select recipient"}
            
            await asyncio.sleep(1)  # Wait for DM to open
            
            # Step 5: Type the message
            message_result = await self.ui_automator.execute_automation("type_text", text=message)
            if not message_result.get("success"):
                return {"success": False, "error": "Could not type message"}
            
            # Step 6: Send message (Enter)
            send_result = await self.ui_automator.execute_automation("press_key", key="enter")
            if not send_result.get("success"):
                return {"success": False, "error": "Could not send message"}
            
            return {
                "success": True,
                "action": "discord_message",
                "recipient": recipient,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sending Discord message: {e}")
            return {"success": False, "error": str(e)}
    
    async def join_voice_channel(self, channel_name: str) -> Dict[str, Any]:
        """Join a voice channel on Discord."""
        try:
            logger.info(f"Joining Discord voice channel: {channel_name}")
            
            # Focus Discord
            focus_result = await self.ui_automator.execute_automation("focus_app", app_name=self.app_name)
            if not focus_result.get("success"):
                return {"success": False, "error": "Could not focus Discord"}
            
            await asyncio.sleep(1)
            
            # Analyze screen to find voice channels
            screen_analysis = await self.ui_automator.execute_automation("analyze_screen")
            if not screen_analysis.get("success"):
                return {"success": False, "error": "Could not analyze Discord interface"}
            
            # Look for the voice channel
            ui_data = screen_analysis["ui_data"]
            channel_element = None
            
            for element in ui_data.get("elements", []):
                element_text = element.get("text", "").lower()
                element_desc = element.get("description", "").lower()
                
                if (channel_name.lower() in element_text or 
                    channel_name.lower() in element_desc or
                    "voice" in element_desc):
                    channel_element = element
                    break
            
            if not channel_element:
                return {"success": False, "error": f"Could not find voice channel: {channel_name}"}
            
            # Click on the voice channel
            coords = channel_element.get("coordinates", {})
            click_result = await self.ui_automator.mouse_controller.click(
                coords.get("x"), coords.get("y")
            )
            
            if not click_result:
                return {"success": False, "error": "Could not click voice channel"}
            
            return {
                "success": True,
                "action": "discord_join_voice",
                "channel": channel_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error joining Discord voice channel: {e}")
            return {"success": False, "error": str(e)}


class SpotifyAutomator:
    """Specialized automation for Spotify."""
    
    def __init__(self, ui_automator: UIAutomator):
        self.ui_automator = ui_automator
        self.app_name = "spotify"
    
    async def play_song(self, song: str, artist: str = None) -> Dict[str, Any]:
        """Play a specific song on Spotify."""
        try:
            search_query = f"{song} {artist}" if artist else song
            logger.info(f"Playing on Spotify: {search_query}")
            
            # Step 1: Focus Spotify
            focus_result = await self.ui_automator.execute_automation("focus_app", app_name=self.app_name)
            if not focus_result.get("success"):
                return {"success": False, "error": "Could not focus Spotify"}
            
            await asyncio.sleep(1)
            
            # Step 2: Open search (Ctrl+L)
            search_result = await self.ui_automator.execute_automation("key_combination", keys=["ctrl", "l"])
            if not search_result.get("success"):
                return {"success": False, "error": "Could not open Spotify search"}
            
            await asyncio.sleep(0.5)
            
            # Step 3: Type search query
            type_result = await self.ui_automator.execute_automation("type_text", text=search_query)
            if not type_result.get("success"):
                return {"success": False, "error": "Could not type search query"}
            
            # Step 4: Press Enter to search
            enter_result = await self.ui_automator.execute_automation("press_key", key="enter")
            if not enter_result.get("success"):
                return {"success": False, "error": "Could not execute search"}
            
            await asyncio.sleep(2)  # Wait for search results
            
            # Step 5: Analyze screen to find the first song result
            screen_analysis = await self.ui_automator.execute_automation("analyze_screen")
            if not screen_analysis.get("success"):
                return {"success": False, "error": "Could not analyze Spotify interface"}
            
            # Look for play button or song result
            ui_data = screen_analysis["ui_data"]
            play_element = None
            
            for element in ui_data.get("elements", []):
                element_desc = element.get("description", "").lower()
                element_text = element.get("text", "").lower()
                
                if ("play" in element_desc or "play" in element_text or
                    song.lower() in element_text or
                    (artist and artist.lower() in element_text)):
                    play_element = element
                    break
            
            if not play_element:
                # Try clicking on the first result area
                return {"success": False, "error": f"Could not find song: {search_query}"}
            
            # Click on the play button or song
            coords = play_element.get("coordinates", {})
            click_result = await self.ui_automator.mouse_controller.click(
                coords.get("x"), coords.get("y")
            )
            
            if not click_result:
                return {"success": False, "error": "Could not click play button"}
            
            return {
                "success": True,
                "action": "spotify_play",
                "song": song,
                "artist": artist,
                "search_query": search_query,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error playing Spotify song: {e}")
            return {"success": False, "error": str(e)}
    
    async def control_playback(self, action: str) -> Dict[str, Any]:
        """Control Spotify playback (play, pause, next, previous)."""
        try:
            logger.info(f"Spotify playback control: {action}")
            
            # Focus Spotify
            focus_result = await self.ui_automator.execute_automation("focus_app", app_name=self.app_name)
            if not focus_result.get("success"):
                return {"success": False, "error": "Could not focus Spotify"}
            
            await asyncio.sleep(0.5)
            
            # Use keyboard shortcuts for playback control
            key_mappings = {
                "play": "space",
                "pause": "space",
                "next": "ctrl+right",
                "previous": "ctrl+left",
                "skip": "ctrl+right"
            }
            
            if action.lower() in key_mappings:
                if "+" in key_mappings[action.lower()]:
                    keys = key_mappings[action.lower()].split("+")
                    control_result = await self.ui_automator.execute_automation("key_combination", keys=keys)
                else:
                    control_result = await self.ui_automator.execute_automation("press_key", key=key_mappings[action.lower()])
                
                if not control_result.get("success"):
                    return {"success": False, "error": f"Could not execute {action}"}
                
                return {
                    "success": True,
                    "action": f"spotify_{action}",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"success": False, "error": f"Unknown playback action: {action}"}
            
        except Exception as e:
            logger.error(f"Error controlling Spotify playback: {e}")
            return {"success": False, "error": str(e)}


class BrowserAutomator:
    """Specialized automation for web browsers."""
    
    def __init__(self, ui_automator: UIAutomator):
        self.ui_automator = ui_automator
        self.browser_apps = ["chrome", "firefox", "edge"]
    
    async def open_website(self, url: str, browser: str = None, new_tab: bool = False) -> Dict[str, Any]:
        """Open a website in a browser."""
        try:
            logger.info(f"Opening website: {url} (new_tab: {new_tab})")
            
            # Determine which browser to use
            target_browser = browser or "chrome"  # Default to Chrome
            
            # Focus browser (with auto-launch if not running)
            focus_result = await self.ui_automator.execute_automation("focus_app", app_name=target_browser)
            if not focus_result.get("success"):
                return {"success": False, "error": f"Could not focus {target_browser}"}
            
            await asyncio.sleep(1)
            
            # Open new tab if requested
            if new_tab:
                new_tab_result = await self.ui_automator.execute_automation("key_combination", keys=["ctrl", "t"])
                if not new_tab_result.get("success"):
                    logger.warning("Could not open new tab, continuing with current tab")
                else:
                    await asyncio.sleep(0.5)
            
            # Focus address bar (Ctrl+L)
            address_result = await self.ui_automator.execute_automation("key_combination", keys=["ctrl", "l"])
            if not address_result.get("success"):
                return {"success": False, "error": "Could not focus address bar"}
            
            await asyncio.sleep(0.5)
            
            # Type URL
            type_result = await self.ui_automator.execute_automation("type_text", text=url)
            if not type_result.get("success"):
                return {"success": False, "error": "Could not type URL"}
            
            # Press Enter to navigate
            enter_result = await self.ui_automator.execute_automation("press_key", key="enter")
            if not enter_result.get("success"):
                return {"success": False, "error": "Could not navigate to URL"}
            
            return {
                "success": True,
                "action": "browser_open_website",
                "url": url,
                "browser": target_browser,
                "new_tab": new_tab,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error opening website: {e}")
            return {"success": False, "error": str(e)}
    
    async def search_web(self, query: str, search_engine: str = "google") -> Dict[str, Any]:
        """Perform a web search."""
        try:
            search_urls = {
                "google": "https://www.google.com/search?q=",
                "bing": "https://www.bing.com/search?q=",
                "duckduckgo": "https://duckduckgo.com/?q="
            }
            
            search_url = search_urls.get(search_engine.lower(), search_urls["google"])
            full_url = search_url + query.replace(" ", "+")
            
            return await self.open_website(full_url)
            
        except Exception as e:
            logger.error(f"Error performing web search: {e}")
            return {"success": False, "error": str(e)}


class SystemAutomator:
    """Automation for system applications and functions."""
    
    def __init__(self, ui_automator: UIAutomator):
        self.ui_automator = ui_automator
    
    async def open_application(self, app_name: str) -> Dict[str, Any]:
        """Open a system application."""
        try:
            logger.info(f"Opening application: {app_name}")
            
            # Use Windows key + R to open Run dialog
            run_result = await self.ui_automator.execute_automation("key_combination", keys=["win", "r"])
            if not run_result.get("success"):
                return {"success": False, "error": "Could not open Run dialog"}
            
            await asyncio.sleep(0.5)
            
            # Common application commands
            app_commands = {
                "calculator": "calc",
                "notepad": "notepad",
                "paint": "mspaint",
                "cmd": "cmd",
                "powershell": "powershell",
                "task manager": "taskmgr",
                "control panel": "control",
                "file explorer": "explorer",
                "registry editor": "regedit"
            }
            
            command = app_commands.get(app_name.lower(), app_name)
            
            # Type command
            type_result = await self.ui_automator.execute_automation("type_text", text=command)
            if not type_result.get("success"):
                return {"success": False, "error": "Could not type application command"}
            
            # Press Enter to execute
            enter_result = await self.ui_automator.execute_automation("press_key", key="enter")
            if not enter_result.get("success"):
                return {"success": False, "error": "Could not execute application command"}
            
            return {
                "success": True,
                "action": "system_open_app",
                "app_name": app_name,
                "command": command,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error opening application: {e}")
            return {"success": False, "error": str(e)}
    
    async def switch_window(self, window_title: str = None) -> Dict[str, Any]:
        """Switch between windows using Alt+Tab."""
        try:
            logger.info("Switching windows")
            
            # Use Alt+Tab to switch windows
            switch_result = await self.ui_automator.execute_automation("key_combination", keys=["alt", "tab"])
            if not switch_result.get("success"):
                return {"success": False, "error": "Could not switch windows"}
            
            return {
                "success": True,
                "action": "system_switch_window",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error switching windows: {e}")
            return {"success": False, "error": str(e)}


class AppAutomationManager:
    """Main manager for all app-specific automations."""
    
    def __init__(self, ui_automator: UIAutomator):
        self.ui_automator = ui_automator
        
        # Initialize app-specific automators
        self.discord = DiscordAutomator(ui_automator)
        self.spotify = SpotifyAutomator(ui_automator)
        self.browser = BrowserAutomator(ui_automator)
        self.system = SystemAutomator(ui_automator)
        
        # Command patterns for app automation (ordered by specificity - most specific first)
        self.automation_patterns = {
            # Discord patterns (very specific)
            r"(?:message|text|dm|send\s+message\s+to)\s+(\w+)\s+(?:on\s+)?discord(?:\s+saying\s+)?(?:\s*[\"'](.+?)[\"'])?": self._handle_discord_message,
            r"join\s+(.+?)\s+(?:voice\s+)?channel\s+(?:on\s+)?discord": self._handle_discord_voice,
            
            # Spotify patterns (very specific)
            r"play\s+(.+?)\s+(?:by\s+(.+?))?\s+(?:on\s+)?spotify": self._handle_spotify_play,
            r"(?:pause|stop)\s+spotify": self._handle_spotify_pause,
            r"(?:next|skip)\s+(?:song\s+)?(?:on\s+)?spotify": self._handle_spotify_next,
            r"(?:previous|back)\s+(?:song\s+)?(?:on\s+)?spotify": self._handle_spotify_previous,
            
            # System application patterns (specific apps)
            r"(?:open|launch|start)\s+(calculator|notepad|paint|cmd|powershell|task\s+manager|control\s+panel|file\s+explorer|registry\s+editor)(?:\s|$)": self._handle_open_application,
            
            # Browser URL patterns (medium specificity - URLs with dots or protocols)
            r"(?:open|go\s+to|navigate\s+to)\s+((?:https?://|www\.|\w+\.\w+)[^\s]*)(?:\s+in\s+(\w+))?": self._handle_open_website,
            
            # Search patterns (medium specificity - explicit search commands)
            r"search\s+(?:for\s+)?(.+?)(?:\s+(?:on|using)\s+(\w+))?$": self._handle_web_search,
            
            # Window switching (specific)
            r"(?:switch|alt\s+tab)\s+(?:window|windows)": self._handle_switch_window,
            
            # Focus application (medium specificity)
            r"(?:switch\s+to|focus\s+on)\s+(.+)": self._handle_focus_application,
            
            # Generic system patterns (least specific - catch-all)
            r"(?:open|launch|start)\s+(.+)": self._handle_open_application,
        }
    
    async def process_automation_command(self, user_input: str) -> Dict[str, Any]:
        """Process user input for app automation commands."""
        try:
            user_input_lower = user_input.lower().strip()
            logger.info(f"Processing automation command: '{user_input_lower}'")
            
            # Check each pattern
            for pattern, handler in self.automation_patterns.items():
                match = re.search(pattern, user_input_lower)
                if match:
                    logger.info(f"Automation pattern matched: {pattern}")
                    result = await handler(match, user_input)
                    
                    if result.get("success"):
                        return {
                            "automation_executed": True,
                            "success": True,
                            "result": result
                        }
                    else:
                        return {
                            "automation_executed": True,
                            "success": False,
                            "error": result.get("error", "Unknown error")
                        }
            
            # No automation pattern matched
            return {"automation_executed": False}
            
        except Exception as e:
            logger.error(f"Error processing automation command: {e}")
            return {
                "automation_executed": True,
                "success": False,
                "error": str(e)
            }
    
    # Handler methods
    async def _handle_discord_message(self, match, original_input: str) -> Dict[str, Any]:
        """Handle Discord message command."""
        try:
            recipient = match.group(1).strip()
            message = match.group(2) if len(match.groups()) > 1 and match.group(2) else "Hello!"
            
            # If no message was captured, ask for it or use a default
            if not message or message.strip() == "":
                message = "Hello from Jarvis!"
            
            return await self.discord.send_message(recipient, message)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_discord_voice(self, match, original_input: str) -> Dict[str, Any]:
        """Handle Discord voice channel join."""
        try:
            channel_name = match.group(1).strip()
            return await self.discord.join_voice_channel(channel_name)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_spotify_play(self, match, original_input: str) -> Dict[str, Any]:
        """Handle Spotify play command."""
        try:
            song = match.group(1).strip()
            artist = match.group(2).strip() if len(match.groups()) > 1 and match.group(2) else None
            
            return await self.spotify.play_song(song, artist)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_spotify_pause(self, match, original_input: str) -> Dict[str, Any]:
        """Handle Spotify pause command."""
        return await self.spotify.control_playback("pause")
    
    async def _handle_spotify_next(self, match, original_input: str) -> Dict[str, Any]:
        """Handle Spotify next command."""
        return await self.spotify.control_playback("next")
    
    async def _handle_spotify_previous(self, match, original_input: str) -> Dict[str, Any]:
        """Handle Spotify previous command."""
        return await self.spotify.control_playback("previous")
    
    async def _handle_open_website(self, match, original_input: str) -> Dict[str, Any]:
        """Handle open website command."""
        try:
            url = match.group(1).strip()
            browser = match.group(2).strip() if len(match.groups()) > 1 and match.group(2) else None
            
            # Add protocol if missing
            if not url.startswith(("http://", "https://")):
                if "." in url:
                    url = "https://" + url
                else:
                    # Treat as search query
                    return await self.browser.search_web(url)
            
            return await self.browser.open_website(url, browser)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_web_search(self, match, original_input: str) -> Dict[str, Any]:
        """Handle web search command."""
        try:
            query = match.group(1).strip()
            search_engine = match.group(2).strip() if len(match.groups()) > 1 and match.group(2) else "google"
            
            # Debug logging to see what we captured
            logger.info(f"Search query extracted: '{query}' from input: '{original_input}'")
            logger.info(f"Search engine: '{search_engine}'")
            
            # Always use new tab for searches
            search_urls = {
                "google": "https://www.google.com/search?q=",
                "bing": "https://www.bing.com/search?q=",
                "duckduckgo": "https://duckduckgo.com/?q="
            }
            
            search_url = search_urls.get(search_engine.lower(), search_urls["google"])
            
            # Proper URL encoding
            import urllib.parse
            encoded_query = urllib.parse.quote_plus(query)
            full_url = search_url + encoded_query
            
            logger.info(f"Final search URL: {full_url}")
            
            return await self.browser.open_website(full_url, new_tab=True)
            
        except Exception as e:
            logger.error(f"Error in web search handler: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_open_application(self, match, original_input: str) -> Dict[str, Any]:
        """Handle open application command."""
        try:
            app_name = match.group(1).strip()
            return await self.system.open_application(app_name)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_focus_application(self, match, original_input: str) -> Dict[str, Any]:
        """Handle focus application command."""
        try:
            app_name = match.group(1).strip()
            return await self.ui_automator.execute_automation("focus_app", app_name=app_name)
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_switch_window(self, match, original_input: str) -> Dict[str, Any]:
        """Handle switch window command."""
        return await self.system.switch_window()
    
    def get_available_automations(self) -> List[Dict[str, Any]]:
        """Get list of available automation commands."""
        return [
            {
                "category": "Discord",
                "commands": [
                    "message [user] on discord",
                    "join [channel] voice channel on discord"
                ]
            },
            {
                "category": "Spotify", 
                "commands": [
                    "play [song] by [artist] on spotify",
                    "pause spotify",
                    "next song on spotify",
                    "previous song on spotify"
                ]
            },
            {
                "category": "Browser",
                "commands": [
                    "open [website]",
                    "search for [query]",
                    "go to [url] in [browser]"
                ]
            },
            {
                "category": "System",
                "commands": [
                    "open [application]",
                    "switch to [application]",
                    "switch windows"
                ]
            }
        ]


# Test function
async def test_app_automators():
    """Test the app automation system."""
    from .ui_automator import UIAutomator
    
    ui_automator = UIAutomator()
    app_manager = AppAutomationManager(ui_automator)
    
    test_commands = [
        "message john on discord",
        "play bohemian rhapsody by queen on spotify",
        "open youtube.com",
        "search for python tutorials",
        "open calculator"
    ]
    
    print("Testing App Automation Commands...")
    
    for command in test_commands:
        print(f"\nTesting: {command}")
        result = await app_manager.process_automation_command(command)
        print(f"Result: {result.get('automation_executed')}")
        if result.get('automation_executed'):
            print(f"Success: {result.get('success')}")
            if not result.get('success'):
                print(f"Error: {result.get('error')}")


if __name__ == "__main__":
    asyncio.run(test_app_automators())
