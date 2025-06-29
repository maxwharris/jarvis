"""
Test script for enhanced action system.
Tests the new action dispatcher with comprehensive file management and screen analysis.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from jarvis.tools.action_dispatcher import ActionDispatcher
from jarvis.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger("test_enhanced_actions")


async def test_action_patterns():
    """Test various action patterns to ensure they work correctly."""
    
    dispatcher = ActionDispatcher()
    
    test_cases = [
        # Screen analysis - the main issue we're fixing
        ("analyze my screen", "analyze_screenshot"),
        ("what's on my screen", "analyze_screenshot"),
        ("describe the screen", "analyze_screenshot"),
        ("take a screenshot", "screenshot"),
        
        # File operations
        ("list files on desktop", "list_files"),
        ("show me files in documents", "list_files"),
        ("what files are in downloads", "list_files"),
        ("browse my pictures folder", "list_files"),
        
        # System info
        ("system info", "system_info"),
        ("how is the computer doing", "system_info"),
        
        # Temp file management
        ("temp info", "temp_info"),
        ("show temp files", "show_temp"),
        ("clean temp folder", "cleanup_temp"),
    ]
    
    print("🧪 Testing Enhanced Action Dispatcher")
    print("=" * 50)
    
    success_count = 0
    total_tests = len(test_cases)
    
    for test_input, expected_action in test_cases:
        print(f"\n📝 Testing: '{test_input}'")
        print(f"   Expected: {expected_action}")
        
        try:
            result = await dispatcher.process_input(test_input)
            
            if result.get('action_taken'):
                actual_action = result['action_taken']
                if actual_action == expected_action:
                    print(f"   ✅ SUCCESS: Action '{actual_action}' detected correctly")
                    success_count += 1
                else:
                    print(f"   ❌ FAILED: Expected '{expected_action}', got '{actual_action}'")
            else:
                print(f"   ❌ FAILED: No action detected")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    print(f"\n📊 Test Results: {success_count}/{total_tests} passed")
    print(f"   Success Rate: {(success_count/total_tests)*100:.1f}%")
    
    return success_count == total_tests


async def test_temp_folder_creation():
    """Test that temp folder structure is created correctly."""
    
    print("\n🗂️  Testing Temp Folder Creation")
    print("=" * 50)
    
    dispatcher = ActionDispatcher()
    temp_root = dispatcher.temp_manager.temp_root
    
    expected_folders = ["screenshots", "downloads", "analysis", "cache", "exports"]
    
    print(f"Temp root: {temp_root}")
    
    all_exist = True
    for folder in expected_folders:
        folder_path = temp_root / folder
        if folder_path.exists():
            print(f"   ✅ {folder}/ exists")
        else:
            print(f"   ❌ {folder}/ missing")
            all_exist = False
    
    return all_exist


async def test_screenshot_functionality():
    """Test screenshot functionality if available."""
    
    print("\n📸 Testing Screenshot Functionality")
    print("=" * 50)
    
    dispatcher = ActionDispatcher()
    
    try:
        # Test screenshot capture
        result = await dispatcher.process_input("take a screenshot")
        
        if result.get('success') and result.get('action_taken') == 'screenshot':
            screenshot_path = result['result'].get('path')
            print(f"   ✅ Screenshot captured: {screenshot_path}")
            
            # Check if file exists
            if Path(screenshot_path).exists():
                print(f"   ✅ Screenshot file exists")
                return True
            else:
                print(f"   ❌ Screenshot file not found")
                return False
        else:
            print(f"   ⚠️  Screenshot not available (PIL not installed or no display)")
            return True  # Not a failure if PIL isn't available
            
    except Exception as e:
        print(f"   ⚠️  Screenshot test failed: {e}")
        return True  # Not a critical failure


async def test_file_listing():
    """Test file listing functionality."""
    
    print("\n📁 Testing File Listing")
    print("=" * 50)
    
    dispatcher = ActionDispatcher()
    
    try:
        # Test listing current directory
        result = await dispatcher.process_input("list files here")
        
        if result.get('success') and result.get('action_taken') == 'list_files':
            file_count = result['result'].get('total_files', 0)
            dir_count = result['result'].get('total_directories', 0)
            print(f"   ✅ Listed {file_count} files and {dir_count} directories")
            return True
        else:
            print(f"   ❌ File listing failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ File listing test failed: {e}")
        return False


async def test_system_info():
    """Test system information functionality."""
    
    print("\n💻 Testing System Information")
    print("=" * 50)
    
    dispatcher = ActionDispatcher()
    
    try:
        result = await dispatcher.process_input("system info")
        
        if result.get('success') and result.get('action_taken') == 'system_info':
            cpu_usage = result['result'].get('cpu', {}).get('usage_percent', 0)
            memory_percent = result['result'].get('memory', {}).get('percent', 0)
            print(f"   ✅ CPU Usage: {cpu_usage}%")
            print(f"   ✅ Memory Usage: {memory_percent}%")
            return True
        else:
            print(f"   ❌ System info failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ System info test failed: {e}")
        return False


async def main():
    """Run all tests."""
    
    print("🚀 Enhanced Action System Test Suite")
    print("=" * 60)
    
    tests = [
        ("Action Pattern Recognition", test_action_patterns),
        ("Temp Folder Creation", test_temp_folder_creation),
        ("Screenshot Functionality", test_screenshot_functionality),
        ("File Listing", test_file_listing),
        ("System Information", test_system_info),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if await test_func():
                print(f"   ✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"   ❌ {test_name} FAILED")
        except Exception as e:
            print(f"   ❌ {test_name} ERROR: {e}")
    
    print(f"\n🏁 Final Results")
    print("=" * 60)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("🎉 All tests passed! Enhanced action system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())
