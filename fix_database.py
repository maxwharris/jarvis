#!/usr/bin/env python3
"""
Database fix utility for Jarvis AI Assistant.
This script will fix the corrupted database issue.
"""

import sys
import os
import sqlite3
import time
import psutil
from pathlib import Path
sys.path.insert(0, 'src')

def find_processes_using_file(file_path):
    """Find processes that are using the specified file."""
    processes = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'open_files']):
            try:
                if proc.info['open_files']:
                    for file_info in proc.info['open_files']:
                        if file_info.path == file_path:
                            processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name']
                            })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        print(f"Error finding processes: {e}")
    
    return processes

def force_close_database_connections():
    """Force close any database connections."""
    try:
        from jarvis.core.config import config
        db_path = config.get_database_path()
        
        print(f"🔍 Checking for processes using: {db_path}")
        
        # Find processes using the database
        processes = find_processes_using_file(db_path)
        
        if processes:
            print(f"⚠️  Found {len(processes)} processes using the database:")
            for proc in processes:
                print(f"   - PID {proc['pid']}: {proc['name']}")
            
            # Ask user if they want to terminate these processes
            response = input("\nTerminate these processes? (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                for proc in processes:
                    try:
                        process = psutil.Process(proc['pid'])
                        process.terminate()
                        print(f"✅ Terminated process {proc['pid']} ({proc['name']})")
                        time.sleep(0.5)  # Give it time to close
                    except Exception as e:
                        print(f"❌ Could not terminate process {proc['pid']}: {e}")
                
                # Wait a bit for processes to close
                time.sleep(2)
            else:
                print("⚠️  Cannot fix database while processes are using it")
                return False
        else:
            print("✅ No processes found using the database")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database processes: {e}")
        return False

def backup_corrupted_database():
    """Backup the corrupted database file."""
    try:
        from jarvis.core.config import config
        db_path = config.get_database_path()
        
        if not os.path.exists(db_path):
            print("ℹ️  Database file does not exist")
            return True
        
        # Create backup filename
        backup_path = f"{db_path}.corrupted_backup_{int(time.time())}"
        
        # Copy the corrupted file
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backed up corrupted database to: {backup_path}")
        
        return backup_path
        
    except Exception as e:
        print(f"❌ Error backing up database: {e}")
        return None

def remove_corrupted_database():
    """Remove the corrupted database file."""
    try:
        from jarvis.core.config import config
        db_path = config.get_database_path()
        
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"✅ Removed corrupted database: {db_path}")
            return True
        else:
            print("ℹ️  Database file does not exist")
            return True
            
    except Exception as e:
        print(f"❌ Error removing corrupted database: {e}")
        return False

def create_fresh_database():
    """Create a fresh, properly initialized database."""
    try:
        from jarvis.core.logging import DatabaseLogHandler, ConversationLogger
        from jarvis.core.config import config
        
        db_path = config.get_database_path()
        
        print(f"🔧 Creating fresh database: {db_path}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Create database handler (this will initialize the database)
        handler = DatabaseLogHandler(db_path)
        
        if handler.db_available:
            print("✅ Database handler initialized successfully")
            
            # Also initialize conversation logger
            conv_logger = ConversationLogger(db_path)
            if conv_logger.db_available:
                print("✅ Conversation logger initialized successfully")
            else:
                print("⚠️  Conversation logger failed to initialize")
            
            # Verify database
            if os.path.exists(db_path):
                size = os.path.getsize(db_path)
                print(f"✅ New database created, size: {size} bytes")
                
                # Test database integrity
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    print(f"✅ Database tables created: {tables}")
                
                return True
            else:
                print("❌ Database file was not created")
                return False
        else:
            print("❌ Database handler failed to initialize")
            return False
            
    except Exception as e:
        print(f"❌ Error creating fresh database: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_functionality():
    """Test that the database is working properly."""
    try:
        from jarvis.core.logging import setup_logging
        
        print("🧪 Testing database functionality...")
        
        # Set up logging system
        logger, conv_logger = setup_logging()
        
        if logger:
            print("✅ Logging system initialized")
            
            # Test logging some messages
            logger.info("Database fix test - INFO message")
            logger.warning("Database fix test - WARNING message")
            logger.error("Database fix test - ERROR message")
            
            print("✅ Successfully logged test messages")
            
            if conv_logger and conv_logger.db_available:
                # Test conversation logging
                session_id = f"test_session_{int(time.time())}"
                conv_logger.start_session(session_id)
                conv_logger.log_interaction(
                    session_id=session_id,
                    input_type="text",
                    user_input="Test user input",
                    ai_response="Test AI response",
                    online_mode=False
                )
                conv_logger.end_session(session_id)
                print("✅ Successfully tested conversation logging")
            
            return True
        else:
            print("❌ Logging system failed to initialize")
            return False
            
    except Exception as e:
        print(f"❌ Error testing database functionality: {e}")
        return False

def main():
    """Main database fix routine."""
    print("🔧 Jarvis Database Fix Utility")
    print("=" * 50)
    print("This utility will fix the 'file is not a database' error")
    print("by removing the corrupted database and creating a fresh one.")
    print()
    
    try:
        # Check if psutil is available
        try:
            import psutil
        except ImportError:
            print("⚠️  psutil not available - cannot check for processes using database")
            print("   You may need to manually close any running Jarvis instances")
            response = input("Continue anyway? (y/n): ").lower().strip()
            if response not in ['y', 'yes']:
                return False
        
        # Step 1: Check current database status
        print("📊 Step 1: Checking current database status")
        print("-" * 40)
        
        from jarvis.core.config import config
        db_path = config.get_database_path()
        
        if os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"Database path: {db_path}")
            print(f"Current size: {size} bytes")
            
            if size < 1024:
                print("⚠️  Database is corrupted (too small)")
            else:
                try:
                    with sqlite3.connect(db_path, timeout=1.0) as conn:
                        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
                        cursor.fetchone()
                    print("✅ Database appears to be valid")
                    print("ℹ️  If you're still getting errors, the database may have other issues")
                except sqlite3.DatabaseError:
                    print("❌ Database is corrupted (SQLite error)")
        else:
            print("ℹ️  Database file does not exist")
        
        # Step 2: Close any processes using the database
        print("\n🔒 Step 2: Closing processes using database")
        print("-" * 45)
        
        if not force_close_database_connections():
            print("❌ Could not close database connections")
            return False
        
        # Step 3: Backup corrupted database
        print("\n💾 Step 3: Backing up corrupted database")
        print("-" * 40)
        
        backup_path = backup_corrupted_database()
        if not backup_path and os.path.exists(db_path):
            print("❌ Could not backup database")
            return False
        
        # Step 4: Remove corrupted database
        print("\n🗑️  Step 4: Removing corrupted database")
        print("-" * 40)
        
        if not remove_corrupted_database():
            print("❌ Could not remove corrupted database")
            return False
        
        # Step 5: Create fresh database
        print("\n🔧 Step 5: Creating fresh database")
        print("-" * 35)
        
        if not create_fresh_database():
            print("❌ Could not create fresh database")
            return False
        
        # Step 6: Test database functionality
        print("\n🧪 Step 6: Testing database functionality")
        print("-" * 40)
        
        if not test_database_functionality():
            print("❌ Database functionality test failed")
            return False
        
        # Success!
        print("\n" + "=" * 50)
        print("🎉 Database fix completed successfully!")
        print()
        print("✅ Corrupted database removed")
        print("✅ Fresh database created")
        print("✅ Database functionality verified")
        print()
        print("🎯 The 'file is not a database' error should now be resolved!")
        print("   You can now run Jarvis normally.")
        
        if backup_path:
            print(f"\n📁 Backup of corrupted database saved to:")
            print(f"   {backup_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Database fix failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✨ Database fix completed successfully!")
    else:
        print("\n💥 Database fix failed!")
    
    input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)
