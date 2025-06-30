#!/usr/bin/env python3
"""
Test the new app automation capabilities.
This demonstrates UI automation for Discord, Spotify, browsers, and system apps.
"""

import sys
import os
sys.path.insert(0, 'src')

import asyncio
from jarvis.tools.action_dispatcher import ActionDispatcher

async def test_app_automation():
    """Test the app automation system."""
    print("🤖 Testing Jarvis App Automation System")
    print("=" * 50)
    
    # Initialize the action dispatcher
    dispatcher = ActionDispatcher()
    
    # Check if UI automation is available
    if not dispatcher.app_automation_manager:
        print("❌ UI automation not available")
        print("📦 Install required packages:")
        print("   pip install pyautogui pygetwindow")
        return
    
    print("✅ UI automation system loaded successfully!")
    print(f"🔧 UI Automator: {dispatcher.ui_automator is not None}")
    print(f"🎯 App Manager: {dispatcher.app_automation_manager is not None}")
    
    # Test commands to demonstrate
    test_commands = [
        # Discord automation
        {
            "command": "message john on discord",
            "description": "Send a message to 'john' on Discord",
            "category": "Discord"
        },
        {
            "command": "join general voice channel on discord", 
            "description": "Join the 'general' voice channel on Discord",
            "category": "Discord"
        },
        
        # Spotify automation
        {
            "command": "play bohemian rhapsody by queen on spotify",
            "description": "Play 'Bohemian Rhapsody' by Queen on Spotify",
            "category": "Spotify"
        },
        {
            "command": "pause spotify",
            "description": "Pause Spotify playback",
            "category": "Spotify"
        },
        {
            "command": "next song on spotify",
            "description": "Skip to next song on Spotify",
            "category": "Spotify"
        },
        
        # Browser automation
        {
            "command": "open youtube.com",
            "description": "Open YouTube in the default browser",
            "category": "Browser"
        },
        {
            "command": "search for python tutorials",
            "description": "Search for 'python tutorials' on Google",
            "category": "Browser"
        },
        {
            "command": "go to github.com in chrome",
            "description": "Open GitHub in Chrome specifically",
            "category": "Browser"
        },
        
        # System automation
        {
            "command": "open calculator",
            "description": "Open the Windows Calculator app",
            "category": "System"
        },
        {
            "command": "switch to notepad",
            "description": "Switch focus to Notepad if it's open",
            "category": "System"
        },
        {
            "command": "switch windows",
            "description": "Use Alt+Tab to switch between windows",
            "category": "System"
        }
    ]
    
    print(f"\n🧪 Testing {len(test_commands)} automation commands...")
    print("=" * 50)
    
    # Test each command
    for i, test_case in enumerate(test_commands, 1):
        command = test_case["command"]
        description = test_case["description"]
        category = test_case["category"]
        
        print(f"\n{i:2d}. [{category}] {command}")
        print(f"    📝 {description}")
        
        try:
            # Process the command
            result = await dispatcher.process_input(command)
            
            if result.get("action_taken") == "app_automation":
                if result.get("success"):
                    print(f"    ✅ SUCCESS: Automation executed")
                    automation_result = result.get("result", {})
                    if automation_result.get("action"):
                        print(f"    🎯 Action: {automation_result['action']}")
                    if automation_result.get("timestamp"):
                        print(f"    ⏰ Time: {automation_result['timestamp']}")
                else:
                    print(f"    ❌ FAILED: {result.get('error', 'Unknown error')}")
            else:
                print(f"    ⚠️  No automation pattern matched")
                
        except Exception as e:
            print(f"    💥 ERROR: {e}")
    
    # Show available automation commands
    print(f"\n📋 Available Automation Categories:")
    print("=" * 50)
    
    if hasattr(dispatcher.app_automation_manager, 'get_available_automations'):
        automations = dispatcher.app_automation_manager.get_available_automations()
        
        for category_info in automations:
            category = category_info["category"]
            commands = category_info["commands"]
            
            print(f"\n🔹 {category}:")
            for cmd in commands:
                print(f"   • {cmd}")
    
    # Show session info
    print(f"\n📊 Automation Session Info:")
    print("=" * 50)
    
    if dispatcher.ui_automator:
        session_info = dispatcher.ui_automator.get_session_info()
        print(f"Session Start: {session_info.get('session_start', 'Unknown')}")
        print(f"Total Actions: {session_info.get('total_actions', 0)}")
        print(f"Automation Available: {session_info.get('automation_available', False)}")
        
        recent_actions = session_info.get('recent_actions', [])
        if recent_actions:
            print(f"\nRecent Actions ({len(recent_actions)}):")
            for action in recent_actions[-5:]:  # Show last 5
                cmd = action.get('command', 'Unknown')
                timestamp = action.get('timestamp', 'Unknown')
                print(f"  • {cmd} at {timestamp}")
    
    print(f"\n🎉 App Automation Test Complete!")
    print("=" * 50)
    print("💡 Tips for using app automation:")
    print("   • Make sure target applications are installed and accessible")
    print("   • Some commands may require the app to be already running")
    print("   • UI automation works by simulating mouse clicks and keyboard input")
    print("   • Commands are processed in real-time - you'll see the automation happen!")
    print("   • Use natural language like 'message john on discord' or 'play music on spotify'")


async def test_specific_automation():
    """Test a specific automation command interactively."""
    print("\n🎯 Interactive Automation Test")
    print("=" * 30)
    
    dispatcher = ActionDispatcher()
    
    if not dispatcher.app_automation_manager:
        print("❌ UI automation not available")
        return
    
    print("Enter an automation command to test (or 'quit' to exit):")
    print("Examples:")
    print("  • message alice on discord")
    print("  • play hello by adele on spotify") 
    print("  • open youtube.com")
    print("  • open calculator")
    
    while True:
        try:
            command = input("\n🤖 Command: ").strip()
            
            if command.lower() in ['quit', 'exit', 'q']:
                break
                
            if not command:
                continue
            
            print(f"🔄 Processing: {command}")
            
            result = await dispatcher.process_input(command)
            
            if result.get("action_taken") == "app_automation":
                if result.get("success"):
                    print("✅ Automation executed successfully!")
                    automation_result = result.get("result", {})
                    for key, value in automation_result.items():
                        if key != "timestamp":
                            print(f"   {key}: {value}")
                else:
                    print(f"❌ Automation failed: {result.get('error')}")
            else:
                print("⚠️  No automation pattern matched this command")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"💥 Error: {e}")
    
    print("\n👋 Interactive test ended")


if __name__ == "__main__":
    print("Jarvis App Automation Test Suite")
    print("Choose test mode:")
    print("1. Full automation test (default)")
    print("2. Interactive test")
    
    try:
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "2":
            asyncio.run(test_specific_automation())
        else:
            asyncio.run(test_app_automation())
            
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled by user")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
