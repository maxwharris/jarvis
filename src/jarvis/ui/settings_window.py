"""
Comprehensive Settings GUI for Jarvis AI Assistant.
Provides user-friendly interface for all configuration options.
"""

import sys
import json
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFormLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QCheckBox, QSlider, QSpinBox, QTextEdit, QFileDialog, QMessageBox,
    QGroupBox, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QProgressBar, QSplitter, QFrame, QScrollArea, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QPalette

from ..core.config import config
from ..core.user_profile import user_profile_manager, SystemDetector
from ..core.logging import get_logger

logger = get_logger("settings_window")


class OllamaModelChecker(QThread):
    """Background thread to check Ollama models."""
    
    models_updated = pyqtSignal(list)
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, host: str):
        super().__init__()
        self.host = host
        
    def run(self):
        """Check Ollama connection and available models."""
        try:
            # Test connection
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models_data = response.json().get('models', [])
                self.models_updated.emit(models_data)
                self.connection_status.emit(True, "Connected")
            else:
                self.connection_status.emit(False, f"HTTP {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.connection_status.emit(False, "Connection refused")
        except requests.exceptions.Timeout:
            self.connection_status.emit(False, "Connection timeout")
        except Exception as e:
            self.connection_status.emit(False, str(e))


class UserProfileTab(QWidget):
    """User profile configuration tab."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile = user_profile_manager.get_current_profile()
        self.detector = SystemDetector()
        self.init_ui()
        self.load_profile_data()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Personal Information Group
        personal_group = QGroupBox("Personal Information")
        personal_layout = QFormLayout(personal_group)
        
        self.display_name_edit = QLineEdit()
        self.system_user_edit = QLineEdit()
        self.home_dir_edit = QLineEdit()
        
        detect_btn = QPushButton("Auto-Detect")
        detect_btn.clicked.connect(self.auto_detect_system_info)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_home_directory)
        
        # Create horizontal layouts for buttons
        system_layout = QHBoxLayout()
        system_layout.addWidget(self.system_user_edit)
        system_layout.addWidget(detect_btn)
        
        home_layout = QHBoxLayout()
        home_layout.addWidget(self.home_dir_edit)
        home_layout.addWidget(browse_btn)
        
        personal_layout.addRow("Display Name:", self.display_name_edit)
        personal_layout.addRow("System Username:", system_layout)
        personal_layout.addRow("Home Directory:", home_layout)
        
        # Communication Preferences Group
        prefs_group = QGroupBox("Communication Preferences")
        prefs_layout = QFormLayout(prefs_group)
        
        self.greeting_combo = QComboBox()
        self.greeting_combo.addItems(["casual", "friendly", "formal"])
        
        self.response_combo = QComboBox()
        self.response_combo.addItems(["brief", "medium", "detailed"])
        
        self.time_combo = QComboBox()
        self.time_combo.addItems(["12h", "24h"])
        
        self.date_combo = QComboBox()
        self.date_combo.addItems(["US", "EU", "ISO"])
        
        prefs_layout.addRow("Greeting Style:", self.greeting_combo)
        prefs_layout.addRow("Response Length:", self.response_combo)
        prefs_layout.addRow("Time Format:", self.time_combo)
        prefs_layout.addRow("Date Format:", self.date_combo)
        
        layout.addWidget(personal_group)
        layout.addWidget(prefs_group)
        layout.addStretch()
    
    def load_profile_data(self):
        """Load current profile data into UI."""
        self.display_name_edit.setText(self.profile.preferences.display_name)
        self.system_user_edit.setText(self.profile.system_username)
        self.home_dir_edit.setText(self.profile.directories.home)
        
        self.greeting_combo.setCurrentText(self.profile.preferences.greeting_style)
        self.response_combo.setCurrentText(self.profile.preferences.response_length)
        self.time_combo.setCurrentText(self.profile.preferences.time_format)
        self.date_combo.setCurrentText(self.profile.preferences.date_format)
    
    def auto_detect_system_info(self):
        """Auto-detect system information."""
        try:
            username = self.detector.get_system_username()
            home_dir = self.detector.get_home_directory()
            
            self.system_user_edit.setText(username)
            self.home_dir_edit.setText(home_dir)
            
            if not self.display_name_edit.text():
                self.display_name_edit.setText(username.title())
                
        except Exception as e:
            QMessageBox.warning(self, "Auto-Detection Error", f"Failed to auto-detect: {e}")
    
    def browse_home_directory(self):
        """Browse for home directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Home Directory", self.home_dir_edit.text()
        )
        if directory:
            self.home_dir_edit.setText(directory)
    
    def get_profile_updates(self) -> Dict[str, Any]:
        """Get profile updates from UI."""
        return {
            'display_name': self.display_name_edit.text(),
            'greeting_style': self.greeting_combo.currentText(),
            'response_length': self.response_combo.currentText(),
            'time_format': self.time_combo.currentText(),
            'date_format': self.date_combo.currentText()
        }


class AIModelsTab(QWidget):
    """AI models configuration tab."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.available_models = []
        self.model_checker = None
        self.init_ui()
        self.load_model_data()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Ollama Connection Group
        connection_group = QGroupBox("Ollama Connection")
        connection_layout = QFormLayout(connection_group)
        
        self.host_edit = QLineEdit()
        self.status_label = QLabel("Checking...")
        self.test_btn = QPushButton("Test Connection")
        self.refresh_btn = QPushButton("Refresh Models")
        
        self.test_btn.clicked.connect(self.test_connection)
        self.refresh_btn.clicked.connect(self.refresh_models)
        
        host_layout = QHBoxLayout()
        host_layout.addWidget(self.host_edit)
        host_layout.addWidget(self.test_btn)
        
        connection_layout.addRow("Host:", host_layout)
        connection_layout.addRow("Status:", self.status_label)
        connection_layout.addRow("", self.refresh_btn)
        
        # Models Selection
        models_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Available Models List
        available_group = QGroupBox("Available Models")
        available_layout = QVBoxLayout(available_group)
        
        self.models_list = QListWidget()
        self.models_list.itemChanged.connect(self.on_model_selection_changed)
        
        self.download_btn = QPushButton("Download Selected")
        self.download_btn.clicked.connect(self.download_models)
        
        available_layout.addWidget(self.models_list)
        available_layout.addWidget(self.download_btn)
        
        # Current Selection
        current_group = QGroupBox("Current Selection")
        current_layout = QFormLayout(current_group)
        
        self.text_model_combo = QComboBox()
        self.vision_model_combo = QComboBox()
        
        current_layout.addRow("Text Model:", self.text_model_combo)
        current_layout.addRow("Vision Model:", self.vision_model_combo)
        
        models_splitter.addWidget(available_group)
        models_splitter.addWidget(current_group)
        
        # Model Parameters Group
        params_group = QGroupBox("Model Parameters")
        params_layout = QFormLayout(params_group)
        
        self.temperature_slider = QSlider(Qt.Orientation.Horizontal)
        self.temperature_slider.setRange(0, 200)
        self.temperature_slider.setValue(70)
        self.temperature_label = QLabel("0.7")
        self.temperature_slider.valueChanged.connect(
            lambda v: self.temperature_label.setText(f"{v/100:.1f}")
        )
        
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 8192)
        self.max_tokens_spin.setValue(2048)
        
        self.context_spin = QSpinBox()
        self.context_spin.setRange(1024, 32768)
        self.context_spin.setValue(4096)
        
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.temperature_slider)
        temp_layout.addWidget(self.temperature_label)
        
        params_layout.addRow("Temperature:", temp_layout)
        params_layout.addRow("Max Tokens:", self.max_tokens_spin)
        params_layout.addRow("Context Size:", self.context_spin)
        
        layout.addWidget(connection_group)
        layout.addWidget(models_splitter)
        layout.addWidget(params_group)
    
    def load_model_data(self):
        """Load current model configuration."""
        self.host_edit.setText(config.models.ollama_host)
        self.text_model_combo.setCurrentText(config.models.text_model)
        self.vision_model_combo.setCurrentText(config.models.vision_model)
        self.temperature_slider.setValue(int(config.models.temperature * 100))
        self.max_tokens_spin.setValue(config.models.max_tokens)
        
        # Start model checking
        self.test_connection()
    
    def test_connection(self):
        """Test Ollama connection."""
        if self.model_checker and self.model_checker.isRunning():
            return
        
        self.status_label.setText("Testing...")
        self.test_btn.setEnabled(False)
        
        self.model_checker = OllamaModelChecker(self.host_edit.text())
        self.model_checker.connection_status.connect(self.on_connection_status)
        self.model_checker.models_updated.connect(self.on_models_updated)
        self.model_checker.start()
    
    def refresh_models(self):
        """Refresh available models."""
        self.test_connection()
    
    def on_connection_status(self, connected: bool, message: str):
        """Handle connection status update."""
        if connected:
            self.status_label.setText(f"✅ {message}")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText(f"❌ {message}")
            self.status_label.setStyleSheet("color: red;")
        
        self.test_btn.setEnabled(True)
    
    def on_models_updated(self, models_data: List[Dict]):
        """Handle models list update."""
        self.available_models = models_data
        self.models_list.clear()
        self.text_model_combo.clear()
        self.vision_model_combo.clear()
        
        for model in models_data:
            name = model.get('name', 'Unknown')
            size = model.get('size', 0)
            size_gb = size / (1024**3) if size > 0 else 0
            
            item = QListWidgetItem(f"{name} ({size_gb:.1f}GB)")
            item.setData(Qt.ItemDataRole.UserRole, model)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            
            self.models_list.addItem(item)
            self.text_model_combo.addItem(name)
            self.vision_model_combo.addItem(name)
        
        # Set current selections
        self.text_model_combo.setCurrentText(config.models.text_model)
        self.vision_model_combo.setCurrentText(config.models.vision_model)
    
    def on_model_selection_changed(self, item):
        """Handle model selection change."""
        selected_count = sum(
            1 for i in range(self.models_list.count())
            if self.models_list.item(i).checkState() == Qt.CheckState.Checked
        )
        self.download_btn.setText(f"Download Selected ({selected_count})")
        self.download_btn.setEnabled(selected_count > 0)
    
    def download_models(self):
        """Download selected models."""
        selected_models = []
        for i in range(self.models_list.count()):
            item = self.models_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                model_data = item.data(Qt.ItemDataRole.UserRole)
                selected_models.append(model_data['name'])
        
        if selected_models:
            QMessageBox.information(
                self, "Download Models",
                f"Would download models: {', '.join(selected_models)}\n"
                "This feature will be implemented in a future update."
            )
    
    def get_model_updates(self) -> Dict[str, Any]:
        """Get model configuration updates."""
        return {
            'ollama_host': self.host_edit.text(),
            'text_model': self.text_model_combo.currentText(),
            'vision_model': self.vision_model_combo.currentText(),
            'temperature': self.temperature_slider.value() / 100.0,
            'max_tokens': self.max_tokens_spin.value()
        }


class DirectoriesTab(QWidget):
    """Directories configuration tab."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profile = user_profile_manager.get_current_profile()
        self.init_ui()
        self.load_directory_data()
    
    def init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Standard Directories Group
        standard_group = QGroupBox("Standard Directories")
        standard_layout = QFormLayout(standard_group)
        
        self.directory_edits = {}
        standard_dirs = ['desktop', 'documents', 'downloads', 'pictures', 'videos', 'music']
        
        for dir_name in standard_dirs:
            edit = QLineEdit()
            browse_btn = QPushButton("Browse")
            browse_btn.clicked.connect(lambda checked, d=dir_name: self.browse_directory(d))
            
            dir_layout = QHBoxLayout()
            dir_layout.addWidget(edit)
            dir_layout.addWidget(browse_btn)
            
            standard_layout.addRow(f"{dir_name.title()}:", dir_layout)
            self.directory_edits[dir_name] = edit
        
        # Auto-detect button
        auto_detect_btn = QPushButton("Auto-Detect Directories")
        auto_detect_btn.clicked.connect(self.auto_detect_directories)
        
        # Custom Directory Aliases Group
        custom_group = QGroupBox("Custom Directory Aliases")
        custom_layout = QVBoxLayout(custom_group)
        
        self.custom_table = QTableWidget(0, 3)
        self.custom_table.setHorizontalHeaderLabels(["Alias", "Path", "Action"])
        self.custom_table.horizontalHeader().setStretchLastSection(True)
        
        add_custom_btn = QPushButton("Add Custom Directory")
        add_custom_btn.clicked.connect(self.add_custom_directory)
        
        custom_layout.addWidget(self.custom_table)
        custom_layout.addWidget(add_custom_btn)
        
        layout.addWidget(standard_group)
        layout.addWidget(auto_detect_btn)
        layout.addWidget(custom_group)
    
    def load_directory_data(self):
        """Load current directory configuration."""
        dirs = self.profile.directories
        
        self.directory_edits['desktop'].setText(dirs.desktop)
        self.directory_edits['documents'].setText(dirs.documents)
        self.directory_edits['downloads'].setText(dirs.downloads)
        self.directory_edits['pictures'].setText(dirs.pictures)
        self.directory_edits['videos'].setText(dirs.videos)
        self.directory_edits['music'].setText(dirs.music)
        
        # Load custom aliases
        self.custom_table.setRowCount(len(dirs.custom_aliases))
        for row, (alias, path) in enumerate(dirs.custom_aliases.items()):
            self.custom_table.setItem(row, 0, QTableWidgetItem(alias))
            self.custom_table.setItem(row, 1, QTableWidgetItem(path))
            
            edit_btn = QPushButton("Edit")
            edit_btn.clicked.connect(lambda checked, r=row: self.edit_custom_directory(r))
            self.custom_table.setCellWidget(row, 2, edit_btn)
    
    def browse_directory(self, dir_name: str):
        """Browse for directory."""
        current_path = self.directory_edits[dir_name].text()
        directory = QFileDialog.getExistingDirectory(
            self, f"Select {dir_name.title()} Directory", current_path
        )
        if directory:
            self.directory_edits[dir_name].setText(directory)
    
    def auto_detect_directories(self):
        """Auto-detect standard directories."""
        try:
            detector = SystemDetector()
            standard_dirs = detector.get_standard_directories()
            
            for dir_name, path in standard_dirs.items():
                if dir_name in self.directory_edits:
                    self.directory_edits[dir_name].setText(path)
            
            QMessageBox.information(self, "Auto-Detection", "Directories auto-detected successfully!")
            
        except Exception as e:
            QMessageBox.warning(self, "Auto-Detection Error", f"Failed to auto-detect: {e}")
    
    def add_custom_directory(self):
        """Add a new custom directory."""
        alias, ok = QInputDialog.getText(self, "Add Custom Directory", "Enter alias name:")
        if ok and alias:
            directory = QFileDialog.getExistingDirectory(
                self, f"Select Directory for '{alias}'"
            )
            if directory:
                row = self.custom_table.rowCount()
                self.custom_table.insertRow(row)
                self.custom_table.setItem(row, 0, QTableWidgetItem(alias))
                self.custom_table.setItem(row, 1, QTableWidgetItem(directory))
                
                edit_btn = QPushButton("Edit")
                edit_btn.clicked.connect(lambda checked, r=row: self.edit_custom_directory(r))
                self.custom_table.setCellWidget(row, 2, edit_btn)
    
    def edit_custom_directory(self, row: int):
        """Edit a custom directory."""
        alias_item = self.custom_table.item(row, 0)
        path_item = self.custom_table.item(row, 1)
        
        if alias_item and path_item:
            # For now, just allow browsing for new path
            directory = QFileDialog.getExistingDirectory(
                self, f"Select Directory for '{alias_item.text()}'", path_item.text()
            )
            if directory:
                path_item.setText(directory)
    
    def get_directory_updates(self) -> Dict[str, str]:
        """Get directory configuration updates."""
        updates = {}
        
        # Standard directories
        for dir_name, edit in self.directory_edits.items():
            updates[dir_name] = edit.text()
        
        # Custom aliases
        custom_aliases = {}
        for row in range(self.custom_table.rowCount()):
            alias_item = self.custom_table.item(row, 0)
            path_item = self.custom_table.item(row, 1)
            if alias_item and path_item:
                custom_aliases[alias_item.text()] = path_item.text()
        
        updates['custom_aliases'] = custom_aliases
        return updates


class SettingsWindow(QMainWindow):
    """Main settings window with tabbed interface."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jarvis AI Assistant - Settings")
        self.setMinimumSize(800, 600)
        self.init_ui()
        
        # Apply dark theme
        self.apply_dark_theme()
    
    def init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.user_tab = UserProfileTab()
        self.models_tab = AIModelsTab()
        self.directories_tab = DirectoriesTab()
        
        self.tab_widget.addTab(self.user_tab, "User Profile")
        self.tab_widget.addTab(self.models_tab, "AI Models")
        self.tab_widget.addTab(self.directories_tab, "Directories")
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("Apply")
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        self.reset_btn = QPushButton("Reset")
        
        self.apply_btn.clicked.connect(self.apply_settings)
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.close)
        self.reset_btn.clicked.connect(self.reset_settings)
        
        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.reset_btn)
        
        layout.addWidget(self.tab_widget)
        layout.addLayout(button_layout)
    
    def apply_dark_theme(self):
        """Apply dark theme to the window."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background-color: #3c3c3c;
            }
            QTabBar::tab {
                background-color: #555555;
                color: #ffffff;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0078d4;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 4px;
                border-radius: 3px;
            }
            QListWidget, QTableWidget {
                background-color: #404040;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 8px;
                background: #404040;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #0078d4;
                border: 1px solid #555555;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
        """)
    
    def apply_settings(self):
        """Apply settings without saving."""
        try:
            # Update user profile
            profile_updates = self.user_tab.get_profile_updates()
            user_profile_manager.update_preferences(profile_updates)
            
            # Update directories
            directory_updates = self.directories_tab.get_directory_updates()
            custom_aliases = directory_updates.pop('custom_aliases', {})
            user_profile_manager.update_directories(directory_updates)
            
            # Update custom aliases
            profile = user_profile_manager.get_current_profile()
            profile.directories.custom_aliases = custom_aliases
            user_profile_manager.save_profile(profile)
            
            # Update model configuration
            model_updates = self.models_tab.get_model_updates()
            for key, value in model_updates.items():
                if hasattr(config.models, key):
                    setattr(config.models, key, value)
            
            QMessageBox.information(self, "Settings Applied", "Settings have been applied successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {e}")
    
    def save_settings(self):
        """Save settings to file."""
        try:
            self.apply_settings()
            config.save_config()
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
    
    def reset_settings(self):
        """Reset settings to defaults."""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Reset user profile
                user_profile_manager._current_profile = None
                profile = user_profile_manager.create_default_profile()
                user_profile_manager.save_profile(profile)
                
                # Reload UI
                self.user_tab.profile = profile
                self.user_tab.load_profile_data()
                self.directories_tab.profile = profile
                self.directories_tab.load_directory_data()
                
                QMessageBox.information(self, "Settings Reset", "Settings have been reset to defaults!")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to reset settings: {e}")


def show_settings_window():
    """Show the settings window."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    window = SettingsWindow()
    window.show()
    
    return window


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SettingsWindow()
    window.show()
    sys.exit(app.exec())
