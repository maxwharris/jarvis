"""
User Profile Management for Jarvis AI Assistant.
Handles user customization, preferences, and system detection.
"""

import os
import json
import platform
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

from .logging import get_logger

logger = get_logger("user_profile")


@dataclass
class UserDirectories:
    """User directory configuration."""
    home: str
    desktop: str
    documents: str
    downloads: str
    pictures: str
    videos: str
    music: str
    custom_aliases: Dict[str, str]


@dataclass
class UserPreferences:
    """User communication and interface preferences."""
    display_name: str
    greeting_style: str  # casual, friendly, formal
    response_length: str  # brief, medium, detailed
    time_format: str  # 12h, 24h
    date_format: str  # US, EU, ISO
    theme: str  # dark, light, auto
    font_size: str  # small, medium, large
    notifications_enabled: bool
    startup_notification: bool
    system_tray: bool


@dataclass
class UserProfile:
    """Complete user profile."""
    system_username: str
    directories: UserDirectories
    preferences: UserPreferences
    created_at: str
    last_updated: str


class SystemDetector:
    """Detects system information and standard directories."""
    
    @staticmethod
    def get_system_username() -> str:
        """Get the current system username."""
        return os.getenv('USERNAME') or os.getenv('USER') or 'user'
    
    @staticmethod
    def get_home_directory() -> str:
        """Get the user's home directory."""
        return str(Path.home())
    
    @staticmethod
    def get_standard_directories() -> Dict[str, str]:
        """Get standard user directories based on OS."""
        home = Path.home()
        system = platform.system().lower()
        
        if system == 'windows':
            return {
                'desktop': str(home / 'Desktop'),
                'documents': str(home / 'Documents'),
                'downloads': str(home / 'Downloads'),
                'pictures': str(home / 'Pictures'),
                'videos': str(home / 'Videos'),
                'music': str(home / 'Music')
            }
        elif system == 'darwin':  # macOS
            return {
                'desktop': str(home / 'Desktop'),
                'documents': str(home / 'Documents'),
                'downloads': str(home / 'Downloads'),
                'pictures': str(home / 'Pictures'),
                'videos': str(home / 'Movies'),
                'music': str(home / 'Music')
            }
        else:  # Linux and others
            return {
                'desktop': str(home / 'Desktop'),
                'documents': str(home / 'Documents'),
                'downloads': str(home / 'Downloads'),
                'pictures': str(home / 'Pictures'),
                'videos': str(home / 'Videos'),
                'music': str(home / 'Music')
            }
    
    @staticmethod
    def validate_directory(path: str) -> bool:
        """Check if a directory exists and is accessible."""
        try:
            path_obj = Path(path)
            return path_obj.exists() and path_obj.is_dir()
        except Exception:
            return False
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get comprehensive system information."""
        return {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.architecture()[0],
            'processor': platform.processor(),
            'hostname': platform.node(),
            'python_version': platform.python_version()
        }


class UserProfileManager:
    """Manages user profiles and preferences."""
    
    def __init__(self, profile_path: str = "config/user_profile.json"):
        self.profile_path = Path(profile_path)
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        self.detector = SystemDetector()
        self._current_profile: Optional[UserProfile] = None
    
    def create_default_profile(self) -> UserProfile:
        """Create a default user profile with auto-detected values."""
        try:
            system_username = self.detector.get_system_username()
            home_dir = self.detector.get_home_directory()
            standard_dirs = self.detector.get_standard_directories()
            
            # Create directories object
            directories = UserDirectories(
                home=home_dir,
                desktop=standard_dirs.get('desktop', str(Path.home() / 'Desktop')),
                documents=standard_dirs.get('documents', str(Path.home() / 'Documents')),
                downloads=standard_dirs.get('downloads', str(Path.home() / 'Downloads')),
                pictures=standard_dirs.get('pictures', str(Path.home() / 'Pictures')),
                videos=standard_dirs.get('videos', str(Path.home() / 'Videos')),
                music=standard_dirs.get('music', str(Path.home() / 'Music')),
                custom_aliases={}
            )
            
            # Create preferences with sensible defaults
            preferences = UserPreferences(
                display_name=system_username.title(),
                greeting_style="friendly",
                response_length="medium",
                time_format="12h",
                date_format="US",
                theme="dark",
                font_size="medium",
                notifications_enabled=True,
                startup_notification=True,
                system_tray=True
            )
            
            # Create complete profile
            now = datetime.now().isoformat()
            profile = UserProfile(
                system_username=system_username,
                directories=directories,
                preferences=preferences,
                created_at=now,
                last_updated=now
            )
            
            logger.info(f"Created default profile for user: {system_username}")
            return profile
            
        except Exception as e:
            logger.error(f"Error creating default profile: {e}")
            raise
    
    def load_profile(self) -> UserProfile:
        """Load user profile from file or create default."""
        try:
            if self.profile_path.exists():
                with open(self.profile_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Convert dict back to dataclasses
                directories = UserDirectories(**data['directories'])
                preferences = UserPreferences(**data['preferences'])
                
                profile = UserProfile(
                    system_username=data['system_username'],
                    directories=directories,
                    preferences=preferences,
                    created_at=data['created_at'],
                    last_updated=data['last_updated']
                )
                
                logger.info(f"Loaded profile for user: {profile.system_username}")
                self._current_profile = profile
                return profile
            else:
                logger.info("No existing profile found, creating default")
                profile = self.create_default_profile()
                self.save_profile(profile)
                self._current_profile = profile
                return profile
                
        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            # Fallback to default profile
            profile = self.create_default_profile()
            self._current_profile = profile
            return profile
    
    def save_profile(self, profile: UserProfile) -> bool:
        """Save user profile to file."""
        try:
            # Update last_updated timestamp
            profile.last_updated = datetime.now().isoformat()
            
            # Convert to dict for JSON serialization
            profile_dict = {
                'system_username': profile.system_username,
                'directories': asdict(profile.directories),
                'preferences': asdict(profile.preferences),
                'created_at': profile.created_at,
                'last_updated': profile.last_updated
            }
            
            # Save to file
            with open(self.profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved profile for user: {profile.system_username}")
            self._current_profile = profile
            return True
            
        except Exception as e:
            logger.error(f"Error saving profile: {e}")
            return False
    
    def get_current_profile(self) -> UserProfile:
        """Get the current user profile."""
        if self._current_profile is None:
            self._current_profile = self.load_profile()
        return self._current_profile
    
    def update_directories(self, directory_updates: Dict[str, str]) -> bool:
        """Update user directories."""
        try:
            profile = self.get_current_profile()
            
            # Update standard directories
            for key, value in directory_updates.items():
                if hasattr(profile.directories, key):
                    setattr(profile.directories, key, value)
                else:
                    # Add to custom aliases
                    profile.directories.custom_aliases[key] = value
            
            return self.save_profile(profile)
            
        except Exception as e:
            logger.error(f"Error updating directories: {e}")
            return False
    
    def update_preferences(self, preference_updates: Dict[str, Any]) -> bool:
        """Update user preferences."""
        try:
            profile = self.get_current_profile()
            
            # Update preferences
            for key, value in preference_updates.items():
                if hasattr(profile.preferences, key):
                    setattr(profile.preferences, key, value)
            
            return self.save_profile(profile)
            
        except Exception as e:
            logger.error(f"Error updating preferences: {e}")
            return False
    
    def add_custom_directory(self, alias: str, path: str) -> bool:
        """Add a custom directory alias."""
        try:
            if not self.detector.validate_directory(path):
                logger.warning(f"Directory does not exist: {path}")
                return False
            
            profile = self.get_current_profile()
            profile.directories.custom_aliases[alias] = path
            
            return self.save_profile(profile)
            
        except Exception as e:
            logger.error(f"Error adding custom directory: {e}")
            return False
    
    def remove_custom_directory(self, alias: str) -> bool:
        """Remove a custom directory alias."""
        try:
            profile = self.get_current_profile()
            
            if alias in profile.directories.custom_aliases:
                del profile.directories.custom_aliases[alias]
                return self.save_profile(profile)
            
            return False
            
        except Exception as e:
            logger.error(f"Error removing custom directory: {e}")
            return False
    
    def resolve_directory_alias(self, alias: str) -> Optional[str]:
        """Resolve a directory alias to its full path with flexible matching."""
        try:
            profile = self.get_current_profile()
            
            # Standard directories mapping
            standard_mapping = {
                'home': profile.directories.home,
                'desktop': profile.directories.desktop,
                'documents': profile.directories.documents,
                'downloads': profile.directories.downloads,
                'pictures': profile.directories.pictures,
                'videos': profile.directories.videos,
                'music': profile.directories.music
            }
            
            # Clean and normalize the alias
            alias_clean = alias.lower().strip()
            
            # Direct match first
            if alias_clean in standard_mapping:
                return standard_mapping[alias_clean]
            
            # Check custom aliases (exact match)
            if alias in profile.directories.custom_aliases:
                return profile.directories.custom_aliases[alias]
            
            # Flexible matching for common variations
            # Remove common words and extract the key directory name
            directory_keywords = {
                'desktop': ['desktop', 'desk'],
                'documents': ['documents', 'docs', 'document'],
                'downloads': ['downloads', 'download', 'dl'],
                'pictures': ['pictures', 'pics', 'images', 'photos', 'picture', 'image', 'photo'],
                'videos': ['videos', 'movies', 'video', 'movie'],
                'music': ['music', 'audio', 'songs', 'song'],
                'home': ['home', 'user']
            }
            
            # Remove common suffixes/prefixes
            words_to_remove = ['folder', 'directory', 'dir', 'the', 'my', 'a', 'an']
            
            # Split alias into words and clean them
            alias_words = [word for word in alias_clean.split() if word not in words_to_remove]
            
            # Try to match against directory keywords
            for dir_name, keywords in directory_keywords.items():
                for keyword in keywords:
                    # Check if any cleaned word matches a keyword
                    if any(keyword in word or word in keyword for word in alias_words):
                        if dir_name in standard_mapping:
                            logger.info(f"Resolved '{alias}' to '{dir_name}' directory")
                            return standard_mapping[dir_name]
                    
                    # Also check if the keyword appears anywhere in the original alias
                    if keyword in alias_clean:
                        if dir_name in standard_mapping:
                            logger.info(f"Resolved '{alias}' to '{dir_name}' directory")
                            return standard_mapping[dir_name]
            
            # Try partial matching on custom aliases
            for custom_alias, path in profile.directories.custom_aliases.items():
                if (custom_alias.lower() in alias_clean or 
                    alias_clean in custom_alias.lower() or
                    any(word in custom_alias.lower() for word in alias_words)):
                    logger.info(f"Resolved '{alias}' to custom alias '{custom_alias}'")
                    return path
            
            logger.debug(f"Could not resolve directory alias: '{alias}'")
            return None
            
        except Exception as e:
            logger.error(f"Error resolving directory alias: {e}")
            return None
    
    def get_directory_info(self) -> Dict[str, Any]:
        """Get comprehensive directory information."""
        try:
            profile = self.get_current_profile()
            
            # Validate all directories
            directory_status = {}
            
            standard_dirs = {
                'home': profile.directories.home,
                'desktop': profile.directories.desktop,
                'documents': profile.directories.documents,
                'downloads': profile.directories.downloads,
                'pictures': profile.directories.pictures,
                'videos': profile.directories.videos,
                'music': profile.directories.music
            }
            
            for name, path in standard_dirs.items():
                directory_status[name] = {
                    'path': path,
                    'exists': self.detector.validate_directory(path),
                    'type': 'standard'
                }
            
            # Add custom aliases
            for alias, path in profile.directories.custom_aliases.items():
                directory_status[alias] = {
                    'path': path,
                    'exists': self.detector.validate_directory(path),
                    'type': 'custom'
                }
            
            return {
                'directories': directory_status,
                'total_directories': len(directory_status),
                'valid_directories': sum(1 for d in directory_status.values() if d['exists'])
            }
            
        except Exception as e:
            logger.error(f"Error getting directory info: {e}")
            return {'directories': {}, 'total_directories': 0, 'valid_directories': 0}
    
    def export_profile(self, export_path: str) -> bool:
        """Export user profile to a file."""
        try:
            profile = self.get_current_profile()
            export_path_obj = Path(export_path)
            
            # Create export data with metadata
            export_data = {
                'jarvis_profile_version': '1.0',
                'exported_at': datetime.now().isoformat(),
                'system_info': self.detector.get_system_info(),
                'profile': {
                    'system_username': profile.system_username,
                    'directories': asdict(profile.directories),
                    'preferences': asdict(profile.preferences),
                    'created_at': profile.created_at,
                    'last_updated': profile.last_updated
                }
            }
            
            with open(export_path_obj, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported profile to: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting profile: {e}")
            return False
    
    def import_profile(self, import_path: str) -> bool:
        """Import user profile from a file."""
        try:
            import_path_obj = Path(import_path)
            
            if not import_path_obj.exists():
                logger.error(f"Import file does not exist: {import_path}")
                return False
            
            with open(import_path_obj, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Validate import data
            if 'profile' not in import_data:
                logger.error("Invalid profile file format")
                return False
            
            profile_data = import_data['profile']
            
            # Create profile from imported data
            directories = UserDirectories(**profile_data['directories'])
            preferences = UserPreferences(**profile_data['preferences'])
            
            profile = UserProfile(
                system_username=profile_data['system_username'],
                directories=directories,
                preferences=preferences,
                created_at=profile_data['created_at'],
                last_updated=datetime.now().isoformat()  # Update timestamp
            )
            
            # Save imported profile
            success = self.save_profile(profile)
            
            if success:
                logger.info(f"Imported profile from: {import_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error importing profile: {e}")
            return False


# Global user profile manager instance
user_profile_manager = UserProfileManager()
