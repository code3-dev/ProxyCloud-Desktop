import sys
import os
import json
import platform
import subprocess
import threading
import time
import psutil
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QTabWidget, QListWidget, QListWidgetItem,
                             QSystemTrayIcon, QMenu, QMessageBox, QDialog, QLineEdit, QComboBox,
                             QCheckBox, QSpinBox, QTextEdit, QScrollArea, QSplitter, QFrame,
                             QInputDialog)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal, QTimer
from PyQt6.QtCore import Qt as QtCore
from PyQt6.QtGui import QIcon, QPixmap, QAction, QFont

# Import custom modules
from utils.proxy_parser import parse_ss_url, parse_vmess_url, parse_vless_url
from utils.xray_config import generate_xray_config, save_config
from utils.xray_process import XrayProcessManager
from utils.system_proxy import SystemProxyManager

class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Settings")
        self.setMinimumSize(800, 600)
        self.parent = parent
        self.setup_ui()
        self.load_base_config()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tabs for different settings
        tabs = QTabWidget()
        
        # DNS Settings Tab
        dns_tab = QWidget()
        dns_layout = QVBoxLayout(dns_tab)
        
        dns_label = QLabel("DNS Settings:")
        dns_layout.addWidget(dns_label)
        
        self.dns_editor = QTextEdit()
        dns_layout.addWidget(self.dns_editor)
        
        # Routing Rules Tab
        routing_tab = QWidget()
        routing_layout = QVBoxLayout(routing_tab)
        
        routing_label = QLabel("Routing Rules:")
        routing_layout.addWidget(routing_label)
        
        self.routing_editor = QTextEdit()
        routing_layout.addWidget(self.routing_editor)
        
        # Outbound Settings Tab
        outbound_tab = QWidget()
        outbound_layout = QVBoxLayout(outbound_tab)
        
        outbound_label = QLabel("Outbound Settings (Read-only):")
        outbound_layout.addWidget(outbound_label)
        
        outbound_info = QLabel("Outbound settings are automatically configured from your connections.")
        outbound_info.setStyleSheet("color: #666; font-style: italic;")
        outbound_layout.addWidget(outbound_info)
        
        self.outbound_editor = QTextEdit()
        self.outbound_editor.setReadOnly(True)  # Make outbound editor read-only
        outbound_layout.addWidget(self.outbound_editor)
        
        # Add tabs
        tabs.addTab(dns_tab, "DNS")
        tabs.addTab(routing_tab, "Routing")
        tabs.addTab(outbound_tab, "Outbound")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset to Default")
        reset_btn.clicked.connect(self.reset_to_default)
        button_layout.addWidget(reset_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def load_base_config(self):
        import json
        
        # First try to load from settings.json
        settings_dir = Path("settings")
        settings_path = settings_dir / "settings.json"
        base_config = None
        
        if settings_path.exists():
            try:
                with open(settings_path, "r") as f:
                    settings = json.load(f)
                    if "base_config" in settings and settings["base_config"]:
                        base_config = settings["base_config"]
                        self.load_config_data(base_config)
                        return
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Failed to load settings: {e}")
        
        # If not found in settings.json, try base.json
        base_path = Path("base.json")
        if base_path.exists():
            try:
                with open(base_path, "r") as f:
                    config = json.load(f)
                self.load_config_data(config)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load base configuration: {e}")
        else:
            QMessageBox.warning(self, "Warning", "Base configuration file not found.")
    
    def load_config_data(self, config):
        import json
        
        # Load DNS settings
        if "dns" in config:
            self.dns_editor.setText(json.dumps(config["dns"], indent=4))
        
        # Load routing rules
        if "routing" in config:
            self.routing_editor.setText(json.dumps(config["routing"], indent=4))
        
        # Load outbound settings
        if "outbounds" in config:
            self.outbound_editor.setText(json.dumps(config["outbounds"], indent=4))
    
    def reset_to_default(self):
        """Reset settings to default values from default.json"""
        import json
        
        # Confirm with user
        reply = QMessageBox.question(self, "Reset to Default", 
                                    "Are you sure you want to reset all settings to default values from default.json?",

                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        # Load default settings from default.json
        try:
            base_path = Path("default.json")

            if base_path.exists():
                with open(base_path, "r") as f:
                    base_config = json.load(f)
                
                # Extract settings from base.json
                default_dns = base_config.get("dns", {})
                default_routing = base_config.get("routing", {})
                
                # Default outbound (keep existing outbound settings)
                current_outbound = {}
                try:
                    current_outbound = json.loads(self.outbound_editor.toPlainText())
                except:
                    current_outbound = base_config.get("outbounds", [{"protocol": "freedom", "tag": "direct"}])
                
                # Update editors
                self.dns_editor.setText(json.dumps(default_dns, indent=4))
                self.routing_editor.setText(json.dumps(default_routing, indent=4))
                
                # Keep outbound as is (read-only)
                self.outbound_editor.setText(json.dumps(current_outbound, indent=4))
                
                QMessageBox.information(self, "Reset Complete", "Settings have been reset to default values from base.json.")
            else:
                QMessageBox.warning(self, "Warning", "base.json not found. Cannot reset to default values.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load base.json: {e}")
            return
    
    def save_config(self):
        import json
        
        try:
            # Parse JSON from editors
            dns_config = json.loads(self.dns_editor.toPlainText())
            routing_config = json.loads(self.routing_editor.toPlainText())
            
            # Get current outbound config (read-only)
            outbound_config = json.loads(self.outbound_editor.toPlainText())
            
            # Create base config
            base_config = {
                "dns": dns_config,
                "routing": routing_config,
                "outbounds": outbound_config
            }
            
            # Save to base.json
            base_path = Path("base.json")
            with open(base_path, "w") as f:
                json.dump(base_config, f, indent=4)
            
            # Update settings.json if parent exists
            if self.parent:
                self.parent.save_settings()
            
            QMessageBox.information(self, "Success", "Configuration saved successfully.")
            self.accept()
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Error", f"Invalid JSON: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {e}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ProxyCloud - Modern UI")
        self.setWindowIcon(QIcon("icons/app.svg"))
        self.setMinimumSize(900, 600)
        
        # Set application icon
        app_icon = QIcon("icons/logo.ico")
        self.setWindowIcon(app_icon)
        
        # Initialize managers
        self.xray_process = XrayProcessManager()
        self.system_proxy = SystemProxyManager()
        
        # Clean log files on startup
        self.clean_log_files()
        
        # Setup UI
        self.setup_ui()
        
        # Setup system tray
        self.setup_system_tray()
        
        # Load saved configs
        self.load_saved_configs()
        
        # Load settings
        self.load_settings()
        
    def setup_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Set modern styling
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #f5f5f7;
                color: #333333;
            }
            QPushButton {
                background-color: #0071e3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0077ed;
            }
            QPushButton:pressed {
                background-color: #005bbf;
            }
            QListWidget, QTextEdit, QLineEdit {
                border: 1px solid #d1d1d6;
                border-radius: 4px;
                background-color: white;
                padding: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #d1d1d6;
                border-radius: 4px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e5e5ea;
                border: 1px solid #d1d1d6;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QCheckBox {
                spacing: 8px;
            }
            QLabel {
                font-size: 13px;
            }
        """)
        
        # Create tabs
        self.tabs = QTabWidget()
        
        # Home tab
        home_tab = QWidget()
        home_layout = QVBoxLayout(home_tab)
        
        # Connection status
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(20, 20, 20, 20)
        
        status_container = QFrame()
        status_container.setObjectName("statusContainer")
        status_container.setStyleSheet("""
            #statusContainer {
                background-color: white;
                border-radius: 10px;
                padding: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        status_container_layout = QHBoxLayout(status_container)
        
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("""
            color: #ff3b30; 
            font-weight: bold; 
            font-size: 16px;
            padding: 5px;
        """)
        status_container_layout.addWidget(self.status_label)
        status_layout.addWidget(status_container, 1)
        
        # Connect/Disconnect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setFixedSize(150, 45)
        self.connect_btn.setObjectName("connectButton")  # For specific styling
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("""
            #connectButton {
                background-color: #34c759;
                font-size: 14px;
                font-weight: bold;
                border-radius: 22px;
            }
            #connectButton:hover {
                background-color: #30b753;
            }
            #connectButton:pressed {
                background-color: #2aa44b;
            }
        """)
        status_layout.addWidget(self.connect_btn)
        
        home_layout.addLayout(status_layout)
        
        # Server list
        server_list_container = QFrame()
        server_list_container.setObjectName("serverListContainer")
        server_list_container.setStyleSheet("""
            #serverListContainer {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        server_list_layout = QVBoxLayout(server_list_container)
        
        server_list_header = QFrame()
        server_list_header.setObjectName("serverListHeader")
        server_list_header.setStyleSheet("""
            #serverListHeader {
                background-color: #f0f0f5;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        server_header_layout = QHBoxLayout(server_list_header)
        server_header_layout.setContentsMargins(15, 10, 15, 10)
        
        server_list_label = QLabel("Available Servers")
        server_list_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #333333;
        """)
        server_header_layout.addWidget(server_list_label)
        server_list_layout.addWidget(server_list_header)
        
        self.server_list = QListWidget()
        self.server_list.setMinimumHeight(300)
        self.server_list.setStyleSheet("""
            QListWidget {
                border: none;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f5;
            }
            QListWidget::item:selected {
                background-color: #e8f0fe;
                color: #1a73e8;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #f5f5f7;
                border-radius: 4px;
            }
        """)
        server_list_layout.addWidget(self.server_list)
        
        home_layout.addWidget(server_list_container)
        
        # Buttons for server management
        button_container = QFrame()
        button_container.setObjectName("buttonContainer")
        button_container.setStyleSheet("""
            #buttonContainer {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                margin-top: 10px;
            }
        """)
        buttons_layout = QHBoxLayout(button_container)
        buttons_layout.setContentsMargins(20, 15, 20, 15)
        buttons_layout.setSpacing(15)
        
        # Create a consistent style for all buttons
        button_style = """
            QPushButton {
                padding: 10px 15px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
        """
        
        add_server_btn = QPushButton("Add Server")
        add_server_btn.setIcon(QIcon("icons/add.svg"))
        add_server_btn.clicked.connect(self.add_server_dialog)
        add_server_btn.setStyleSheet(button_style)
        buttons_layout.addWidget(add_server_btn)
        
        import_btn = QPushButton("Import from URL")
        import_btn.setIcon(QIcon("icons/import.svg"))
        import_btn.clicked.connect(self.import_from_url_dialog)
        import_btn.setStyleSheet(button_style)
        buttons_layout.addWidget(import_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setIcon(QIcon("icons/remove.svg"))
        remove_btn.clicked.connect(self.remove_selected_server)
        remove_btn.setStyleSheet(button_style)
        buttons_layout.addWidget(remove_btn)
        
        test_ping_btn = QPushButton("Test Ping")
        test_ping_btn.setIcon(QIcon("icons/ping.svg"))
        test_ping_btn.clicked.connect(self.test_ping_all_servers)
        test_ping_btn.setStyleSheet(button_style)
        buttons_layout.addWidget(test_ping_btn)
        
        home_layout.addWidget(button_container)
        
        # Settings tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(15)
        
        # System proxy settings
        proxy_group = QFrame()
        proxy_group.setObjectName("settingsGroup")
        proxy_group.setStyleSheet("""
            #settingsGroup {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                padding: 5px;
            }
        """)
        proxy_layout = QVBoxLayout(proxy_group)
        proxy_layout.setContentsMargins(15, 15, 15, 15)
        
        proxy_header = QLabel("System Proxy Settings")
        proxy_header.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #333333;
            margin-bottom: 10px;
        """)
        proxy_layout.addWidget(proxy_header)
        
        self.enable_system_proxy = QCheckBox("Enable System Proxy")
        self.enable_system_proxy.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #0071e3;
                border: 2px solid #0071e3;
                border-radius: 3px;
                image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'%3E%3C/polyline%3E%3C/svg%3E");
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #d1d1d6;
                border-radius: 3px;
                background-color: white;
            }
        """)
        self.enable_system_proxy.toggled.connect(self.toggle_system_proxy)
        self.enable_system_proxy.toggled.connect(self.save_settings)
        proxy_layout.addWidget(self.enable_system_proxy)
        
        # Tray settings
        self.minimize_to_tray = QCheckBox("Minimize to Tray on Close")
        self.minimize_to_tray.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #0071e3;
                border: 2px solid #0071e3;
                border-radius: 3px;
                image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'%3E%3C/polyline%3E%3C/svg%3E");
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #d1d1d6;
                border-radius: 3px;
                background-color: white;
            }
        """)
        self.minimize_to_tray.toggled.connect(self.save_settings)
        proxy_layout.addWidget(self.minimize_to_tray)
        
        settings_layout.addWidget(proxy_group)
        
        # Auto start/connect settings
        auto_group = QFrame()
        auto_group.setObjectName("settingsGroup")
        auto_group.setStyleSheet("""
            #settingsGroup {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                padding: 5px;
            }
        """)
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setContentsMargins(15, 15, 15, 15)
        
        auto_header = QLabel("Startup Settings")
        auto_header.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #333333;
            margin-bottom: 10px;
        """)
        auto_layout.addWidget(auto_header)
        
        self.auto_start = QCheckBox("Start on System Startup")
        self.auto_start.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #0071e3;
                border: 2px solid #0071e3;
                border-radius: 3px;
                image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'%3E%3C/polyline%3E%3C/svg%3E");
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #d1d1d6;
                border-radius: 3px;
                background-color: white;
            }
        """)
        self.auto_start.toggled.connect(self.toggle_auto_start)
        self.auto_start.toggled.connect(self.save_settings)
        auto_layout.addWidget(self.auto_start)
        
        self.auto_connect = QCheckBox("Auto Connect on Startup")
        self.auto_connect.setStyleSheet("""
            QCheckBox {
                font-size: 13px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:checked {
                background-color: #0071e3;
                border: 2px solid #0071e3;
                border-radius: 3px;
                image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'%3E%3C/polyline%3E%3C/svg%3E");
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #d1d1d6;
                border-radius: 3px;
                background-color: white;
            }
        """)
        self.auto_connect.toggled.connect(self.save_settings)
        auto_layout.addWidget(self.auto_connect)
        
        settings_layout.addWidget(auto_group)
        
        # Advanced settings button
        advanced_btn = QPushButton("Advanced Settings")
        advanced_btn.setIcon(QIcon("icons/settings.svg"))
        advanced_btn.setStyleSheet("""
            QPushButton {
                margin-top: 10px;
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                background-color: #5856d6;
            }
            QPushButton:hover {
                background-color: #4a49c0;
            }
            QPushButton:pressed {
                background-color: #3c3b9d;
            }
        """)
        advanced_btn.clicked.connect(self.show_advanced_settings)
        settings_layout.addWidget(advanced_btn)
        
        settings_layout.addStretch()
        
        # Logs tab
        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        logs_layout.setContentsMargins(20, 20, 20, 20)
        
        log_container = QFrame()
        log_container.setObjectName("logContainer")
        log_container.setStyleSheet("""
            #logContainer {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        log_header = QFrame()
        log_header.setObjectName("logHeader")
        log_header.setStyleSheet("""
            #logHeader {
                background-color: #f0f0f5;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid #e0e0e0;
            }
        """)
        log_header_layout = QHBoxLayout(log_header)
        log_header_layout.setContentsMargins(15, 10, 15, 10)
        
        log_label = QLabel("Application Logs")
        log_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            color: #333333;
        """)
        log_header_layout.addWidget(log_label)
        log_layout.addWidget(log_header)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                border: none;
                padding: 10px;
                background-color: white;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                color: #333333;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        logs_layout.addWidget(log_container, 1)
        
        clear_logs_btn = QPushButton("Clear Logs")
        clear_logs_btn.setIcon(QIcon("icons/clear.svg"))
        clear_logs_btn.setStyleSheet("""
            QPushButton {
                margin-top: 10px;
                padding: 10px 15px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        clear_logs_btn.clicked.connect(self.clear_logs)
        logs_layout.addWidget(clear_logs_btn)
        
        # Add tabs to tab widget with icons
        self.tabs.addTab(home_tab, QIcon("icons/home.svg"), "Home")
        self.tabs.addTab(settings_tab, QIcon("icons/settings.svg"), "Settings")
        self.tabs.addTab(logs_tab, QIcon("icons/logs.svg"), "Logs")
        
        # Set tab size and style
        self.tabs.setIconSize(QSize(18, 18))
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d1d1d6;
                border-radius: 8px;
                background-color: white;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #e5e5ea;
                border: 1px solid #d1d1d6;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 10px 16px;
                margin-right: 4px;
                min-width: 100px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0071e3;
            }
            QTabBar::tab:hover:!selected {
                background-color: #ebebf0;
            }
        """)
        
        main_layout.addWidget(self.tabs)
        
        self.setCentralWidget(main_widget)
    
    def setup_system_tray(self):
        # Create system tray icon
        tray_icon_pixmap = QIcon("icons/logo.png")
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(tray_icon_pixmap)
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        connect_action = QAction("Connect", self)
        connect_action.triggered.connect(self.connect_from_tray)
        tray_menu.addAction(connect_action)
        
        disconnect_action = QAction("Disconnect", self)
        disconnect_action.triggered.connect(self.disconnect_from_tray)
        tray_menu.addAction(disconnect_action)
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close_application)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
    
    def clean_log_files(self):
        """Clean access.log and error.log files on application startup"""
        try:
            # Clean access.log
            if os.path.exists("access.log"):
                with open("access.log", "w") as f:
                    f.truncate(0)
            
            # Clean error.log
            if os.path.exists("error.log"):
                with open("error.log", "w") as f:
                    f.truncate(0)
        except Exception as e:
            print(f"Error cleaning log files: {e}")
    
    def load_saved_configs(self):
        # Load saved configurations
        pass
    
    def toggle_connection(self):
        # Toggle VPN connection
        if self.xray_process.is_running:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        # Get the selected server
        selected_items = self.server_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Server Selected", "Please select a server to connect to.")
            return
        
        selected_item = selected_items[0]
        config_data = selected_item.data(QtCore.ItemDataRole.UserRole)
        
        if not config_data:
            QMessageBox.warning(self, "Invalid Server", "The selected server configuration is invalid.")
            return
        
        # Update UI to show connecting status
        self.connect_btn.setText("Connecting...")
        self.connect_btn.setEnabled(False)
        self.status_label.setText("Status: Connecting...")
        self.status_label.setStyleSheet("""
            color: #ff9500; 
            font-weight: bold; 
            font-size: 16px;
        """)
        QApplication.processEvents()  # Update UI immediately
        
        # Generate Xray configuration
        xray_config = generate_xray_config(config_data, False)
        
        # Save the configuration to a temporary file
        config_dir = Path("configs")
        config_dir.mkdir(exist_ok=True)
        config_path = str(config_dir / "current_config.json")
        
        if save_config(xray_config, config_path):
            # Start Xray with the configuration
            if self.xray_process.start(config_path):
                # Enable system proxy if needed
                if self.enable_system_proxy.isChecked():
                    self.system_proxy.enable()
                
                # Update UI
                self.connect_btn.setText("Disconnect")
                self.connect_btn.setEnabled(True)
                self.connect_btn.setStyleSheet("""
                    #connectButton {
                        background-color: #ff3b30;
                        font-size: 14px;
                        font-weight: bold;
                        border-radius: 22px;
                    }
                    #connectButton:hover {
                        background-color: #e6352c;
                    }
                    #connectButton:pressed {
                        background-color: #cc2f27;
                    }
                """)
                self.status_label.setText("Status: Connected")
                self.status_label.setStyleSheet("""
                    color: #34c759; 
                    font-weight: bold; 
                    font-size: 16px;
                """)
                
                # Log the connection
                self.log_text.append(f"✅ Connected to {config_data.get('tag', 'server')}")
            else:
                # Reset UI on failure
                self.connect_btn.setText("Connect")
                self.connect_btn.setEnabled(True)
                self.connect_btn.setStyleSheet("""
                    #connectButton {
                        background-color: #34c759;
                        font-size: 14px;
                        font-weight: bold;
                        border-radius: 22px;
                    }
                    #connectButton:hover {
                        background-color: #30b753;
                    }
                    #connectButton:pressed {
                        background-color: #2aa44b;
                    }
                """)
                self.status_label.setText("Status: Disconnected")
                self.status_label.setStyleSheet("""
                    color: #ff3b30; 
                    font-weight: bold; 
                    font-size: 16px;
                """)
                QMessageBox.critical(self, "Connection Failed", "Failed to start Xray. Check the logs for details.")
                self.log_text.append("❌ Failed to start Xray process")
        else:
            # Reset UI on failure
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("""
                color: #ff3b30; 
                font-weight: bold; 
                font-size: 16px;
            """)
            QMessageBox.critical(self, "Configuration Error", "Failed to save Xray configuration.")
            self.log_text.append("❌ Configuration error: Failed to save Xray configuration")
    
    def disconnect(self):
        # Update UI to show disconnecting status
        self.connect_btn.setText("Disconnecting...")
        self.connect_btn.setEnabled(False)
        self.status_label.setText("Status: Disconnecting...")
        self.status_label.setStyleSheet("""
            color: #ff9500; 
            font-weight: bold; 
            font-size: 16px;
        """)
        QApplication.processEvents()  # Update UI immediately
        
        # Stop Xray
        if self.xray_process.stop():
            # Disable system proxy if it was enabled
            if self.system_proxy.is_enabled:
                self.system_proxy.disable()
            
            # Update UI
            self.connect_btn.setText("Connect")
            self.connect_btn.setEnabled(True)
            self.connect_btn.setStyleSheet("""
                #connectButton {
                    background-color: #34c759;
                    font-size: 14px;
                    font-weight: bold;
                    border-radius: 22px;
                }
                #connectButton:hover {
                    background-color: #30b753;
                }
                #connectButton:pressed {
                    background-color: #2aa44b;
                }
            """)
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("""
                color: #ff3b30; 
                font-weight: bold; 
                font-size: 16px;
            """)
            
            # Log the disconnection
            self.log_text.append("🔌 Disconnected")
        else:
            # Reset UI on failure
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setEnabled(True)
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("""
                color: #34c759; 
                font-weight: bold; 
                font-size: 16px;
            """)
            QMessageBox.critical(self, "Disconnection Failed", "Failed to stop Xray. Check the logs for details.")
            self.log_text.append("❌ Failed to stop Xray process")
    
    def connect_from_tray(self):
        # Connect from system tray
        if not self.xray_process.is_running:
            self.show()
            self.connect()
    
    def disconnect_from_tray(self):
        # Disconnect from system tray
        if self.xray_process.is_running:
            self.disconnect()
    
    def add_server_dialog(self):
        # Show dialog to add a new server
        url, ok = QInputDialog.getText(self, "Add Server", "Enter proxy URL (SS/VMess/VLESS):")
        if ok and url:
            self.add_server(url)
    
    def import_from_url_dialog(self):
        # Show dialog to import server from URL
        clipboard = QApplication.clipboard()
        url = clipboard.text()
        if url:
            self.add_server(url)
        else:
            QMessageBox.warning(self, "Empty Clipboard", "Clipboard does not contain any text.")
    

    
    def remove_selected_server(self):
        # Remove selected server from list
        selected_items = self.server_list.selectedItems()
        if selected_items:
            for item in selected_items:
                row = self.server_list.row(item)
                self.server_list.takeItem(row)
            
            # Log the removal
            self.log_text.append("Removed selected server(s)")
        else:
            QMessageBox.warning(self, "No Server Selected", "Please select a server to remove.")
            
    def add_server(self, url):
        # Add a server from URL
        from utils.proxy_parser import parse_proxy_url
        
        config = parse_proxy_url(url)
        if config:
            # Create a list item for the server
            item = QListWidgetItem(config.get('tag', 'Unknown Server'))
            item.setData(QtCore.ItemDataRole.UserRole, config)
            
            # Add icon based on protocol
            protocol = config.get('type', '').lower()
            if protocol == 'ss':
                item.setIcon(QIcon.fromTheme("network-vpn", QIcon("icons/ss.svg")))
            elif protocol == 'vmess':
                item.setIcon(QIcon.fromTheme("network-vpn", QIcon("icons/vmess.svg")))
            elif protocol == 'vless':
                item.setIcon(QIcon.fromTheme("network-vpn", QIcon("icons/vless.svg")))
            
            # Add to server list
            self.server_list.addItem(item)
            
            # Log the addition
            self.log_text.append(f"Added server: {config.get('tag', 'Unknown Server')}")
        else:
            QMessageBox.warning(self, "Invalid URL", "The URL is not a valid SS/VMess/VLESS proxy URL.")
    
    def test_ping_all_servers(self):
        """Test ping delay for all servers in the list"""
        from utils.ping_utils import measure_configs_delay
        
        # Get all configs from the server list
        configs = []
        for i in range(self.server_list.count()):
            item = self.server_list.item(i)
            config = item.data(QtCore.ItemDataRole.UserRole)
            if config:
                configs.append(config)
        
        if not configs:
            QMessageBox.warning(self, "No Servers", "No servers available to test.")
            return
        
        # Show progress dialog
        self.log_text.append("Testing ping delay for all servers...")
        
        # Use a separate thread to avoid freezing the UI
        class PingThread(QThread):
            finished = pyqtSignal(list)
            
            def __init__(self, configs, test_url):
                super().__init__()
                self.configs = configs
                self.test_url = test_url
            
            def run(self):
                # Measure delay for all configs
                results = measure_configs_delay(self.configs, self.test_url)
                self.finished.emit(results)
        
        # Create and start the thread
        self.ping_thread = PingThread(configs, "https://www.gstatic.com/generate_204")
        self.ping_thread.finished.connect(self.update_ping_results)
        self.ping_thread.start()
    
    def update_ping_results(self, configs):
        """Update the server list with ping results"""
        # Update each item in the server list
        for i in range(self.server_list.count()):
            item = self.server_list.item(i)
            config = item.data(QtCore.ItemDataRole.UserRole)
            
            # Find the matching config in the results
            for result in configs:
                if (result.get('server') == config.get('server') and 
                    result.get('port') == config.get('port') and 
                    result.get('type') == config.get('type')):
                    
                    # Update the config with delay information
                    config['delay'] = result.get('delay')
                    item.setData(QtCore.ItemDataRole.UserRole, config)
                    
                    # Update the display text
                    delay_text = "Timeout" if config['delay'] is None else f"{int(config['delay'])}ms"
                    item.setText(f"{config.get('tag', 'Unknown Server')} [{delay_text}]")
                    break
        
        self.log_text.append("Ping test completed for all servers.")
        
        # Sort the server list by delay (lowest first, timeouts last)
        items = []
        for i in range(self.server_list.count()):
            items.append(self.server_list.takeItem(0))
        
        # Sort items by delay
        items.sort(key=lambda x: float('inf') if x.data(QtCore.ItemDataRole.UserRole).get('delay') is None 
                  else x.data(QtCore.ItemDataRole.UserRole).get('delay'))
        
        # Add sorted items back to the list
        for item in items:
            self.server_list.addItem(item)
        
        # Select the first item (lowest delay)
        if self.server_list.count() > 0:
            self.server_list.setCurrentRow(0)
    
    def toggle_system_proxy(self, enabled):
        # Toggle system proxy
        if enabled:
            if self.xray_process.is_running:
                self.system_proxy.enable()
                self.log_text.append("System proxy enabled")
            else:
                self.system_proxy.disable()
                self.log_text.append("System proxy disabled")
    
    def toggle_auto_start(self, enabled):
        # Toggle auto start on system startup
        import platform
        import os
        from pathlib import Path
        
        if platform.system() == "Windows":
            import winreg
            app_path = os.path.abspath(sys.argv[0])
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            
            if enabled:
                winreg.SetValueEx(key, "ProxyCloud", 0, winreg.REG_SZ, f'"{app_path}"')
                self.log_text.append("Auto start enabled")
            else:
                try:
                    winreg.DeleteValue(key, "ProxyCloud")
                except FileNotFoundError:
                    pass
                self.log_text.append("Auto start disabled")
            
            winreg.CloseKey(key)
        elif platform.system() == "Linux":
            autostart_dir = Path.home() / ".config" / "autostart"
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_file = autostart_dir / "proxycloud.desktop"
            
            if enabled:
                app_path = os.path.abspath(sys.argv[0])
                with open(desktop_file, "w") as f:
                    f.write(f"[Desktop Entry]\nType=Application\nName=ProxyCloud\nExec={app_path}\nTerminal=false\nStartupNotify=false\n")
                self.log_text.append("Auto start enabled")
            else:
                if desktop_file.exists():
                    desktop_file.unlink()
                self.log_text.append("Auto start disabled")
    
    def clear_logs(self):
        # Clear logs
        self.log_text.clear()
        self.log_text.append("Logs cleared")
    
    def show_advanced_settings(self):
        # Show advanced settings dialog
        dialog = AdvancedSettingsDialog(self)
        dialog.exec()
    
    def save_settings(self):
        # Save settings
        import json
        
        settings = {
            "system_proxy": self.enable_system_proxy.isChecked(),
            "auto_start": self.auto_start.isChecked(),
            "auto_connect": self.auto_connect.isChecked(),
            "minimize_to_tray": self.minimize_to_tray.isChecked(),
            "servers": []
        }
        
        # Save server list
        for i in range(self.server_list.count()):
            item = self.server_list.item(i)
            config = item.data(QtCore.ItemDataRole.UserRole)
            if config:
                settings["servers"].append(config)
        
        # Load base.json if it exists
        base_config = {}
        base_path = Path("base.json")
        if base_path.exists():
            try:
                with open(base_path, "r") as f:
                    base_config = json.load(f)
                settings["base_config"] = base_config
            except Exception as e:
                self.log_text.append(f"Error loading base.json: {e}")
        
        # Save to file
        settings_dir = Path("settings")
        settings_dir.mkdir(exist_ok=True)
        settings_path = settings_dir / "settings.json"
        
        try:
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)
            self.log_text.append("Settings saved")
        except Exception as e:
            self.log_text.append(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Settings Error", f"Failed to save settings: {e}")
    
    def load_settings(self):
        # Load settings
        import json
        
        settings_dir = Path("settings")
        settings_path = settings_dir / "settings.json"
        
        if settings_path.exists():
            try:
                with open(settings_path, "r") as f:
                    settings = json.load(f)
                
                # Apply settings
                self.enable_system_proxy.setChecked(settings.get("system_proxy", False))
                self.auto_start.setChecked(settings.get("auto_start", False))
                self.auto_connect.setChecked(settings.get("auto_connect", False))
                self.minimize_to_tray.setChecked(settings.get("minimize_to_tray", True))
                
                # Apply auto_start setting
                if settings.get("auto_start", False):
                    self.toggle_auto_start(True)
                
                # Load servers
                self.server_list.clear()
                for config in settings.get("servers", []):
                    item = QListWidgetItem(config.get("tag", "Unknown Server"))
                    item.setData(QtCore.ItemDataRole.UserRole, config)
                    
                    # Add icon based on protocol
                    protocol = config.get("type", "").lower()
                    if protocol == "ss":
                        item.setIcon(QIcon.fromTheme("network-vpn", QIcon("icons/ss.svg")))
                    elif protocol == "vmess":
                        item.setIcon(QIcon.fromTheme("network-vpn", QIcon("icons/vmess.svg")))
                    elif protocol == "vless":
                        item.setIcon(QIcon.fromTheme("network-vpn", QIcon("icons/vless.svg")))
                    
                    # Add to server list
                    self.server_list.addItem(item)
                
                self.log_text.append("Settings loaded")
                
                # Apply system proxy and TUN mode settings if Xray is running
                if self.xray_process.is_running:
                    if settings.get("system_proxy", False):
                        self.system_proxy.enable()
                    if settings.get("tun_mode", False):
                        self.tun_manager.enable()
                
                # Auto connect if enabled
                if settings.get("auto_connect", False) and self.server_list.count() > 0:
                    self.server_list.setCurrentRow(0)
                    self.connect()
            except Exception as e:
                self.log_text.append(f"Failed to load settings: {e}")
        else:
            self.log_text.append("No settings file found, using defaults")
    
    def close_application(self):
        # Clean up and close application
        if self.xray_process.is_running:
            self.disconnect()
        
        # Save settings
        self.save_settings()
        
        # Close application
        QApplication.quit()
    
    def closeEvent(self, event):
        # Override close event to minimize to tray instead of closing
        if self.minimize_to_tray.isChecked():
            event.ignore()
            self.hide()
        else:
            # Stop Xray process if it's running
            if self.xray_process.is_running:
                self.disconnect()
            event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    # Ensure cleanup when application exits
    app.aboutToQuit.connect(lambda: cleanup(window))
    
    sys.exit(app.exec())

def cleanup(window):
    # Make sure Xray is stopped when application exits
    if window.xray_process.is_running:
        window.disconnect()
    
    # Kill any remaining Xray processes
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            if 'xray' in proc.info['name'].lower():
                try:
                    psutil.Process(proc.info['pid']).terminate()
                except Exception as e:
                    print(f"Error terminating Xray process: {e}")
    except Exception as e:
        print(f"Error cleaning up Xray processes: {e}")

if __name__ == "__main__":
    main()