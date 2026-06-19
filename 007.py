import sys
import os
import shutil
import threading
import time
import winsound
import json
import subprocess
import random
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QFrame, QTreeWidget, QTreeWidgetItem,
                             QSystemTrayIcon, QMenu, QAction, QMessageBox, QPushButton,
                             QSplitter, QInputDialog, QLineEdit, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QPalette

# ============================================
# CONFIGURATION
# ============================================
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".bin_v73_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {
        "auto_startup": False, 
        "sound_enabled": True, 
        "theme": "green",
        "show_hidden": False,
        "confirm_delete": True
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

# ============================================
# FILE OPERATIONS
# ============================================
class FileOperations:
    clipboard = None
    clipboard_action = None

    @staticmethod
    def copy_to_clipboard(source_path, action='copy'):
        FileOperations.clipboard = source_path
        FileOperations.clipboard_action = action
        return True

    @staticmethod
    def paste_from_clipboard(dest_dir):
        if not FileOperations.clipboard or not os.path.exists(FileOperations.clipboard):
            return False, "Clipboard empty"
        try:
            source = FileOperations.clipboard
            dest = os.path.join(dest_dir, os.path.basename(source))
            if os.path.exists(dest):
                return False, f"File already exists: {os.path.basename(source)}"
            if FileOperations.clipboard_action == 'copy':
                if os.path.isdir(source):
                    shutil.copytree(source, dest)
                else:
                    shutil.copy2(source, dest)
            else:
                shutil.move(source, dest)
                FileOperations.clipboard = None
                FileOperations.clipboard_action = None
            return True, "Success"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def delete_file(path):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            return True, "Deleted"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def rename_file(old_path, new_name):
        try:
            dir_path = os.path.dirname(old_path)
            new_path = os.path.join(dir_path, new_name)
            os.rename(old_path, new_path)
            return True, new_path
        except Exception as e:
            return False, str(e)

    @staticmethod
    def create_folder(parent_path, name):
        try:
            new_path = os.path.join(parent_path, name)
            os.makedirs(new_path, exist_ok=False)
            return True, new_path
        except Exception as e:
            return False, str(e)

# ============================================
# USB MONITOR
# ============================================
class USBMonitor(QThread):
    usb_detected = pyqtSignal(str, str)
    usb_removed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.known_drives = set()

    def get_usb_drives(self):
        import ctypes
        from ctypes import wintypes
        drives = []
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i in range(26):
            if bitmask & (1 << i):
                drive_letter = f"{chr(65 + i)}:"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_letter + "\\")
                if drive_type == 2:
                    vol_name_buf = ctypes.create_unicode_buffer(261)
                    serial = wintypes.DWORD()
                    max_comp_len = wintypes.DWORD()
                    file_flags = wintypes.DWORD()
                    fs_name_buf = ctypes.create_unicode_buffer(261)
                    ctypes.windll.kernel32.GetVolumeInformationW(
                        drive_letter + "\\", vol_name_buf, 261,
                        ctypes.byref(serial), ctypes.byref(max_comp_len),
                        ctypes.byref(file_flags), fs_name_buf, 261
                    )
                    volume_name = vol_name_buf.value if vol_name_buf.value else "UNKNOWN_DEVICE"
                    drives.append((drive_letter, volume_name))
        return drives

    def run(self):
        self.known_drives = {d[0] for d in self.get_usb_drives()}
        while self.running:
            try:
                current_drives = self.get_usb_drives()
                current_letters = {d[0] for d in current_drives}
                for letter, name in current_drives:
                    if letter not in self.known_drives:
                        self.usb_detected.emit(letter, name)
                for letter in self.known_drives:
                    if letter not in current_letters:
                        self.usb_removed.emit(letter)
                self.known_drives = current_letters
            except Exception as e:
                print(f"Monitor error: {e}")
            time.sleep(1.5)

    def stop(self):
        self.running = False

# ============================================
# LIVE SCANNER - James Bond Style Continuous Scan
# ============================================
class LiveScanner(QThread):
    file_found = pyqtSignal(str, str, str, str, str)  # path, name, type, size, status
    scan_progress = pyqtSignal(int, str)  # progress, message
    scan_complete = pyqtSignal()

    def __init__(self, drive_letter):
        super().__init__()
        self.drive_letter = drive_letter
        self.running = True
        self.scanned_paths = set()
        self.total_files = 0

    def get_file_type(self, ext):
        types = {
            '.jpg': 'IMAGE', '.jpeg': 'IMAGE', '.png': 'IMAGE', '.gif': 'IMAGE',
            '.bmp': 'IMAGE', '.tiff': 'IMAGE', '.webp': 'IMAGE',
            '.mp4': 'VIDEO', '.avi': 'VIDEO', '.mkv': 'VIDEO', '.mov': 'VIDEO',
            '.wmv': 'VIDEO', '.flv': 'VIDEO',
            '.pdf': 'DOCUMENT', '.doc': 'DOCUMENT', '.docx': 'DOCUMENT',
            '.xls': 'SPREADSHEET', '.xlsx': 'SPREADSHEET', '.csv': 'DATA',
            '.ppt': 'PRESENTATION', '.pptx': 'PRESENTATION',
            '.txt': 'TEXT', '.md': 'TEXT', '.json': 'CODE', '.xml': 'CODE',
            '.html': 'CODE', '.css': 'CODE', '.js': 'CODE', '.py': 'CODE',
            '.cpp': 'CODE', '.c': 'CODE', '.java': 'CODE',
            '.exe': 'PROGRAM', '.dll': 'SYSTEM', '.bat': 'SCRIPT',
            '.zip': 'ARCHIVE', '.rar': 'ARCHIVE', '.7z': 'ARCHIVE',
            '.tar': 'ARCHIVE', '.gz': 'ARCHIVE',
            '.mp3': 'AUDIO', '.wav': 'AUDIO', '.flac': 'AUDIO',
            '.iso': 'DISC_IMAGE', '.dmg': 'DISC_IMAGE'
        }
        return types.get(ext, 'UNKNOWN')

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def run(self):
        drive_path = f"{self.drive_letter}\\"
        if not os.path.exists(drive_path):
            return

        # Phase 1: Quick scan - emit files one by one with delay (James Bond effect)
        self.scan_folder_live(drive_path, 0)

        # Phase 2: Continuous "monitoring" loop
        loop_count = 0
        while self.running:
            loop_count += 1
            progress = min(70 + (loop_count % 30), 99)
            messages = [
                "Monitoring file integrity...",
                "Scanning for new files...",
                "Verifying checksums...",
                "Cross-referencing database...",
                "Analyzing metadata...",
                "Checking permissions...",
                "Indexing contents...",
                "Decrypting headers...",
            ]
            msg = messages[loop_count % len(messages)]
            self.scan_progress.emit(progress, msg)
            time.sleep(0.8)

        self.scan_complete.emit()

    def scan_folder_live(self, path, depth):
        """Scan folder and emit files one by one with typing effect delay"""
        if depth > 3 or not self.running:
            return

        try:
            items = sorted(os.listdir(path))
            for item in items:
                if not self.running:
                    return

                item_path = os.path.join(path, item)
                is_dir = os.path.isdir(item_path)

                if item.startswith('.'):
                    continue

                self.total_files += 1

                if is_dir:
                    self.file_found.emit(
                        item_path, item, "FOLDER", "-", "[DIR]"
                    )
                    # Recursive scan with delay
                    self.scan_folder_live(item_path, depth + 1)
                else:
                    try:
                        stat = os.stat(item_path)
                        ext = Path(item).suffix.lower()
                        file_type = self.get_file_type(ext)
                        size = self.format_size(stat.st_size)
                        mtime = time.ctime(stat.st_mtime)[:16]

                        # Random "security status"
                        statuses = ["VERIFIED", "SCANNED", "CHECKED", "CLEARED", "APPROVED"]
                        status = random.choice(statuses)

                        self.file_found.emit(
                            item_path, item, file_type, size, status
                        )
                    except:
                        pass

                # James Bond typing effect - small delay between files
                if self.total_files % 5 == 0:
                    time.sleep(0.05)

                # Update progress
                progress = min(int((self.total_files / 50) * 70), 70)
                self.scan_progress.emit(progress, f"Analyzing: {item[:30]}...")

        except PermissionError:
            pass
        except Exception as e:
            print(f"Scan error: {e}")

    def stop(self):
        self.running = False

# ============================================
# BIN V7.4 - James Bond Live Scanner
# ============================================
class BIN_V73(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.current_drive = None
        self.volume_name = None
        self.current_path = None
        self.scanning = False
        self.scan_progress_val = 0
        self.live_scanner = None
        self.tree_items = {}  # path -> QTreeWidgetItem mapping

        self.setWindowTitle("◈ BADAN INTELIJEN NEGARA V7.4 ◈")
        self.setMinimumSize(1600, 1000)

        self.setup_theme()
        self.build_ui()
        self.setup_tray()
        self.setup_monitor()

        self.showFullScreen()

        if self.config.get("auto_startup"):
            self.hide()

    def setup_theme(self):
        theme = self.config.get("theme", "green")
        themes = {
            "green": {
                "primary": "#00ffaa", "secondary": "#008866", "alert": "#ff4444", 
                "warn": "#ffaa00", "bg": "#0a0a14", "panel": "#11111f", "selected": "#003333"
            },
            "amber": {
                "primary": "#ffaa00", "secondary": "#886600", "alert": "#ff4444",
                "warn": "#00ffaa", "bg": "#14100a", "panel": "#1f1a11", "selected": "#332200"
            },
            "red": {
                "primary": "#ff4444", "secondary": "#886666", "alert": "#ffaa00",
                "warn": "#00ffaa", "bg": "#140a0a", "panel": "#1f1111", "selected": "#330000"
            },
            "cyan": {
                "primary": "#00aaff", "secondary": "#006688", "alert": "#ff4444",
                "warn": "#ffaa00", "bg": "#0a0a14", "panel": "#11111f", "selected": "#001a33"
            }
        }
        self.colors = themes.get(theme, themes["green"])

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(self.colors["bg"]))
        palette.setColor(QPalette.WindowText, QColor(self.colors["primary"]))
        palette.setColor(QPalette.Base, QColor(self.colors["panel"]))
        palette.setColor(QPalette.Text, QColor(self.colors["primary"]))
        palette.setColor(QPalette.Highlight, QColor(self.colors["selected"]))
        palette.setColor(QPalette.HighlightedText, QColor(self.colors["primary"]))
        self.setPalette(palette)

    def build_ui(self):
        self.central = QWidget()
        self.setCentralWidget(self.central)
        self.layout = QVBoxLayout(self.central)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.build_header()
        self.build_content()
        self.build_footer()
        self.show_screen("waiting")

    def build_header(self):
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #001a1a, stop:0.5 #003333, stop:1 #001a1a);
                border-bottom: 3px solid {self.colors["primary"]};
            }}
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(30, 10, 30, 10)

        badge = QLabel("◈")
        badge.setFont(QFont("Consolas", 36, QFont.Bold))
        badge.setStyleSheet(f"color: {self.colors['primary']};")
        layout.addWidget(badge)

        title = QLabel("BADAN INTELIJEN NEGARA V7.4")
        title.setFont(QFont("Consolas", 28, QFont.Bold))
        title.setStyleSheet(f"color: {self.colors['primary']}; letter-spacing: 5px;")
        layout.addWidget(title)
        layout.addStretch()

        self.path_label = QLabel("STANDBY")
        self.path_label.setFont(QFont("Consolas", 11))
        self.path_label.setStyleSheet(f"""
            color: {self.colors['secondary']};
            padding: 5px 15px;
            border: 1px solid {self.colors['secondary']};
            background: rgba(0, 136, 102, 0.1);
        """)
        layout.addWidget(self.path_label)

        layout.addStretch()

        self.status_label = QLabel("● STANDBY MODE")
        self.status_label.setFont(QFont("Consolas", 14, QFont.Bold))
        self.status_label.setStyleSheet(f"color: {self.colors['alert']};")
        layout.addWidget(self.status_label)

        classified = QLabel("[CLASSIFIED]")
        classified.setFont(QFont("Consolas", 12, QFont.Bold))
        classified.setStyleSheet(f"color: {self.colors['alert']}; border: 1px solid {self.colors['alert']}; padding: 3px 10px;")
        layout.addWidget(classified)

        self.layout.addWidget(header)

    def build_content(self):
        self.content = QFrame()
        self.content.setStyleSheet(f"background: {self.colors['bg']};")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self.waiting_widget = self.create_waiting_screen()
        self.scanning_widget = self.create_scanning_screen()
        self.browser_widget = self.create_browser_screen()
        self.empty_widget = self.create_empty_screen()

        self.content_layout.addWidget(self.waiting_widget)
        self.content_layout.addWidget(self.scanning_widget)
        self.content_layout.addWidget(self.browser_widget)
        self.content_layout.addWidget(self.empty_widget)

        self.layout.addWidget(self.content)

    def create_waiting_screen(self):
        widget = QFrame()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        self.waiting_title = QLabel("AWAITING SECURE DEVICE")
        self.waiting_title.setFont(QFont("Consolas", 26, QFont.Bold))
        self.waiting_title.setStyleSheet(f"""
            color: {self.colors['primary']};
            padding: 40px 60px;
            border: 3px solid {self.colors['primary']};
            background: rgba(0, 255, 170, 0.05);
        """)
        self.waiting_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.waiting_title)

        sub = QLabel("Insert classified USB device to access secure data")
        sub.setFont(QFont("Consolas", 13))
        sub.setStyleSheet(f"color: {self.colors['secondary']}; margin-top: 30px;")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        hint = QLabel("ESC = Windowed  |  F11 = Fullscreen  |  F5 = Refresh  |  DEL = Delete")
        hint.setFont(QFont("Consolas", 10))
        hint.setStyleSheet(f"color: {self.colors['secondary']}; margin-top: 50px;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        return widget

    def create_scanning_screen(self):
        widget = QFrame()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        self.scan_title = QLabel("INITIATING SECURITY PROTOCOL")
        self.scan_title.setFont(QFont("Consolas", 34, QFont.Bold))
        self.scan_title.setStyleSheet(f"color: {self.colors['primary']};")
        self.scan_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.scan_title)

        self.scan_device = QLabel()
        self.scan_device.setFont(QFont("Consolas", 16))
        self.scan_device.setStyleSheet(f"color: {self.colors['warn']}; margin-top: 20px;")
        self.scan_device.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.scan_device)

        self.scan_info = QLabel("Establishing secure connection...")
        self.scan_info.setFont(QFont("Consolas", 14))
        self.scan_info.setStyleSheet(f"color: {self.colors['secondary']}; margin-top: 25px;")
        self.scan_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.scan_info)

        self.progress_bar = QLabel("[" + "░" * 70 + "]")
        self.progress_bar.setFont(QFont("Consolas", 13))
        self.progress_bar.setStyleSheet(f"color: {self.colors['primary']};")
        self.progress_bar.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.progress_bar)

        self.scan_stats = QLabel()
        self.scan_stats.setFont(QFont("Consolas", 11))
        self.scan_stats.setStyleSheet(f"color: {self.colors['secondary']};")
        self.scan_stats.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.scan_stats)

        return widget

    def create_browser_screen(self):
        widget = QFrame()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top info bar with LIVE indicator
        self.drive_info = QLabel()
        self.drive_info.setFont(QFont("Consolas", 13, QFont.Bold))
        self.drive_info.setStyleSheet(f"""
            color: {self.colors['primary']};
            padding: 10px 15px;
            border: 1px solid {self.colors['primary']};
            background: rgba(0, 255, 170, 0.08);
        """)
        layout.addWidget(self.drive_info)

        # Live scanning indicator bar
        self.live_bar = QLabel("● LIVE SCANNING ACTIVE")
        self.live_bar.setFont(QFont("Consolas", 11, QFont.Bold))
        self.live_bar.setStyleSheet(f"""
            color: {self.colors['alert']};
            padding: 5px 15px;
            border: 1px solid {self.colors['alert']};
            background: rgba(255, 68, 68, 0.1);
        """)
        layout.addWidget(self.live_bar)

        # Toolbar
        toolbar = QFrame()
        toolbar.setFixedHeight(45)
        toolbar.setStyleSheet(f"""
            QFrame {{ background: {self.colors['panel']}; border: 1px solid {self.colors['secondary']}; }}
            QPushButton {{
                background: rgba(0, 255, 170, 0.1);
                color: {self.colors['primary']};
                border: 1px solid {self.colors['primary']};
                padding: 5px 15px;
                font-family: Consolas;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: rgba(0, 255, 170, 0.2);
                border: 2px solid {self.colors['primary']};
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(10)

        self.btn_copy = QPushButton("📋 COPY")
        self.btn_copy.clicked.connect(self.copy_selected)
        toolbar_layout.addWidget(self.btn_copy)

        self.btn_cut = QPushButton("✂️ CUT")
        self.btn_cut.clicked.connect(self.cut_selected)
        toolbar_layout.addWidget(self.btn_cut)

        self.btn_paste = QPushButton("📎 PASTE")
        self.btn_paste.clicked.connect(self.paste_selected)
        toolbar_layout.addWidget(self.btn_paste)

        self.btn_delete = QPushButton("🗑️ DELETE")
        self.btn_delete.clicked.connect(self.delete_selected)
        toolbar_layout.addWidget(self.btn_delete)

        self.btn_rename = QPushButton("✏️ RENAME")
        self.btn_rename.clicked.connect(self.rename_selected)
        toolbar_layout.addWidget(self.btn_rename)

        self.btn_new_folder = QPushButton("📁 NEW FOLDER")
        self.btn_new_folder.clicked.connect(self.create_new_folder)
        toolbar_layout.addWidget(self.btn_new_folder)

        toolbar_layout.addStretch()

        self.clipboard_label = QLabel("Clipboard: Empty")
        self.clipboard_label.setFont(QFont("Consolas", 10))
        self.clipboard_label.setStyleSheet(f"color: {self.colors['secondary']};")
        toolbar_layout.addWidget(self.clipboard_label)

        layout.addWidget(toolbar)

        # Splitter: Tree (left) + Right panel (small tree above live console)
        splitter = QSplitter(Qt.Horizontal)

        # LEFT: Tree View
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["NAME", "TYPE", "SIZE", "STATUS", "SECURITY"])
        self.tree.setColumnWidth(0, 350)
        self.tree.setColumnWidth(1, 100)
        self.tree.setColumnWidth(2, 90)
        self.tree.setColumnWidth(3, 100)
        self.tree.setColumnWidth(4, 120)
        self.tree.setFont(QFont("Consolas", 11))
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {self.colors['panel']};
                color: {self.colors['primary']};
                border: 1px solid {self.colors['secondary']};
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 6px 5px;
                border-bottom: 1px solid rgba(0, 136, 102, 0.15);
            }}
            QTreeWidget::item:selected {{
                background: {self.colors['selected']};
                color: {self.colors['primary']};
                border: 1px solid {self.colors['primary']};
            }}
            QTreeWidget::item:hover {{
                background: rgba(0, 255, 170, 0.08);
            }}
            QHeaderView::section {{
                background: {self.colors['panel']};
                color: {self.colors['primary']};
                padding: 8px;
                border: 1px solid {self.colors['secondary']};
                font-weight: bold;
            }}
        """)
        self.tree.itemExpanded.connect(self.on_item_expanded)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        splitter.addWidget(self.tree)

        # RIGHT: Panel containing a small tree above the live console
        right_panel = QFrame()
        right_panel.setStyleSheet(f"""
            QFrame {{
                background: {self.colors['panel']};
                border: 1px solid {self.colors['secondary']};
            }}
        """)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        # Small tree above console (mirror of left tree)
        # Small tree above console (mirror of left tree) - use helper
        self.right_tree = self.create_small_tree(max_height=120)
        right_layout.addWidget(self.right_tree)

        # Live console (restored size)
        self.console = QTextEdit()
        self.console.setFont(QFont("Consolas", 10))
        self.console.setStyleSheet(f"""
            QTextEdit {{
                background: {self.colors['panel']};
                color: {self.colors['primary']};
                border: 1px solid {self.colors['secondary']};
                padding: 10px;
            }}
        """)
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Live scanning output...")

        right_layout.addWidget(self.console)

        splitter.addWidget(right_panel)
        splitter.setSizes([700, 500])

        layout.addWidget(splitter)

        return widget

    def create_small_tree(self, max_height=120):
        """Create a compact QTreeWidget (used above the live console)."""
        tree = QTreeWidget()
        tree.setHeaderLabels(["NAME", "TYPE", "SIZE", "STATUS", "SECURITY"])
        tree.setColumnWidth(0, 350)
        tree.setColumnWidth(1, 100)
        tree.setColumnWidth(2, 90)
        tree.setColumnWidth(3, 100)
        tree.setColumnWidth(4, 120)
        tree.setFont(QFont("Consolas", 11))
        tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {self.colors['panel']};
                color: {self.colors['primary']};
                border: none;
            }}
            QHeaderView::section {{
                background: {self.colors['panel']};
                color: {self.colors['primary']};
                padding: 6px;
                border: 1px solid {self.colors['secondary']};
                font-weight: bold;
            }}
        """)
        tree.setMaximumHeight(max_height)
        tree.itemExpanded.connect(self.on_item_expanded)
        tree.itemClicked.connect(self.on_item_clicked)
        tree.setContextMenuPolicy(Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self.show_context_menu)
        return tree

    def create_empty_screen(self):
        widget = QFrame()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel("DEVICE REMOVED")
        label.setFont(QFont("Consolas", 28, QFont.Bold))
        label.setStyleSheet(f"color: {self.colors['alert']};")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        sub = QLabel("Secure connection terminated")
        sub.setFont(QFont("Consolas", 13))
        sub.setStyleSheet(f"color: {self.colors['secondary']}; margin-top: 20px;")
        sub.setAlignment(Qt.AlignCenter)
        layout.addWidget(sub)

        return widget

    def build_footer(self):
        footer = QFrame()
        footer.setFixedHeight(50)
        footer.setStyleSheet(f"""
            QFrame {{
                background: #001111;
                border-top: 2px solid {self.colors['primary']};
            }}
        """)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(25, 5, 25, 5)

        left = QLabel("ENCRYPTION: AES-256 | PROTOCOL: OMEGA-7 | CLEARANCE: LEVEL 5 | EYES ONLY")
        left.setFont(QFont("Consolas", 10))
        left.setStyleSheet(f"color: {self.colors['secondary']};")
        layout.addWidget(left)

        layout.addStretch()

        self.time_label = QLabel()
        self.time_label.setFont(QFont("Consolas", 10))
        self.time_label.setStyleSheet(f"color: {self.colors['secondary']};")
        layout.addWidget(self.time_label)

        self.layout.addWidget(footer)

        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.update_clock()

    def update_clock(self):
        self.time_label.setText(time.strftime("%Y-%m-%d %H:%M:%S UTC"))

    def show_screen(self, screen_name):
        screens = {
            "waiting": self.waiting_widget,
            "scanning": self.scanning_widget,
            "browser": self.browser_widget,
            "empty": self.empty_widget
        }
        for name, widget in screens.items():
            widget.setVisible(name == screen_name)

    # ============================================
    # LIVE SCANNING - James Bond Effect
    # ============================================
    def on_usb_inserted(self, drive_letter, volume_name):
        self.current_drive = drive_letter
        self.volume_name = volume_name

        self.show_screen("scanning")
        self.show_and_raise()

        self.status_label.setText(f"● SCANNING: {drive_letter}")
        self.status_label.setStyleSheet(f"color: {self.colors['warn']};")

        self.scan_device.setText(f"TARGET: {volume_name} ({drive_letter})")
        self.scan_info.setText("Establishing secure connection...")
        self.scan_progress_val = 0
        self.scanning = True

        # Start animation timer
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.update_scan_animation)
        self.anim_timer.start(80)

        self.play_sound("detect")

        # Start live scanner thread
        self.live_scanner = LiveScanner(drive_letter)
        self.live_scanner.file_found.connect(self.on_file_found)
        self.live_scanner.scan_progress.connect(self.on_scan_progress)
        self.live_scanner.scan_complete.connect(self.on_scan_complete)
        self.live_scanner.start()

    def on_file_found(self, path, name, file_type, size, status):
        """Called when live scanner finds a file - add to tree immediately"""
        # Add to console
        timestamp = time.strftime("%H:%M:%S")
        if file_type == "FOLDER":
            self.console.append(f"[{timestamp}] 📁 SCANNING DIR: {name}")
        else:
            self.console.append(f"[{timestamp}] 📄 FOUND: {name} | {file_type} | {size} | [{status}]")

        # Auto-scroll console
        scrollbar = self.console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        # Add to tree (lazy - only add root level items, children on expand)
        drive_path = f"{self.current_drive}\\"
        if path == drive_path or os.path.dirname(path) == drive_path:
            # Root level item
            item = QTreeWidgetItem(self.tree)
            if file_type == "FOLDER":
                item.setText(0, f"📁 {name}")
                item.setText(1, "FOLDER")
                item.setText(2, "-")
                item.setText(3, "[DIR]")
                item.setText(4, "PENDING")
                item.setData(0, Qt.UserRole, path)
                item.setData(1, Qt.UserRole, True)  # is_dir
                dummy = QTreeWidgetItem(item)
                dummy.setText(0, "Loading...")
            else:
                item.setText(0, f"📄 {name}")
                item.setText(1, file_type)
                item.setText(2, size)
                item.setText(3, status)
                item.setText(4, "VERIFIED")
                item.setData(0, Qt.UserRole, path)
                item.setData(1, Qt.UserRole, False)

            self.tree_items[path] = item

    def on_scan_progress(self, progress, message):
        """Update progress bar and info"""
        self.scan_progress_val = progress
        self.scan_info.setText(message)

        filled = "█" * (progress // 2)
        empty = "░" * (35 - progress // 2)
        self.progress_bar.setText(f"[{filled}{empty}] {progress}%")

    def on_scan_complete(self):
        """Initial scan complete - switch to browser but keep live"""
        pass  # We switch to browser after a delay

    def update_scan_animation(self):
        """Continuous scanning animation"""
        self.scan_progress_val = (self.scan_progress_val + 1) % 100

        if self.scan_progress_val < 70:
            # Initial scan phase
            dots = "." * ((self.scan_progress_val // 10) % 4)
            self.scan_title.setText(f"INITIATING SECURITY PROTOCOL{dots}")
        else:
            # Switch to browser after initial scan
            if self.scanning:
                self.scanning = False
                self.show_screen("browser")
                self.status_label.setText(f"● LIVE MONITORING: {self.current_drive}")
                self.status_label.setStyleSheet(f"color: {self.colors['primary']};")

                self.drive_info.setText(
                    f"◈ DEVICE: {self.volume_name} ({self.current_drive})  |  "
                    f"STATUS: LIVE SCANNING  |  "
                    f"CLEARANCE: LEVEL 5"
                )

                self.path_label.setText(f"PATH: {self.current_drive}\\")
                self.play_sound("complete")

            # Live monitoring animation
            dots = "." * ((self.scan_progress_val // 5) % 4)
            self.live_bar.setText(f"● LIVE SCANNING ACTIVE{dots}")

            # Random console updates
            if self.scan_progress_val % 10 == 0:
                timestamp = time.strftime("%H:%M:%S")
                msgs = [
                    "Verifying checksum integrity...",
                    "Cross-referencing threat database...",
                    "Monitoring file changes...",
                    "Scanning for new content...",
                    "Analyzing metadata headers...",
                    "Checking permission levels...",
                ]
                self.console.append(f"[{timestamp}] >> {random.choice(msgs)}")
                scrollbar = self.console.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())

    # ============================================
    # TREE OPERATIONS
    # ============================================
    def on_item_expanded(self, item):
        if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
            item.removeChild(item.child(0))
            path = item.data(0, Qt.UserRole)
            if path and os.path.isdir(path):
                self.load_folder_contents(item, path)

    def load_folder_contents(self, parent_item, path):
        try:
            items = sorted(os.listdir(path))
            for item_name in items:
                item_path = os.path.join(path, item_name)
                is_dir = os.path.isdir(item_path)

                if item_name.startswith('.') and not self.config.get("show_hidden", False):
                    continue

                tree_item = QTreeWidgetItem(parent_item)

                if is_dir:
                    tree_item.setText(0, f"📁 {item_name}")
                    tree_item.setText(1, "FOLDER")
                    tree_item.setText(2, "-")
                    tree_item.setText(3, "[DIR]")
                    tree_item.setText(4, "PENDING")
                    tree_item.setData(0, Qt.UserRole, item_path)
                    tree_item.setData(1, Qt.UserRole, True)
                    dummy = QTreeWidgetItem(tree_item)
                    dummy.setText(0, "Loading...")
                else:
                    try:
                        stat = os.stat(item_path)
                        ext = Path(item_name).suffix.lower()
                        file_type = self.get_file_type_name(ext)
                        size = self.format_size(stat.st_size)

                        tree_item.setText(0, f"📄 {item_name}")
                        tree_item.setText(1, file_type)
                        tree_item.setText(2, size)
                        tree_item.setText(3, "VERIFIED")
                        tree_item.setText(4, "CLEARED")
                        tree_item.setData(0, Qt.UserRole, item_path)
                        tree_item.setData(1, Qt.UserRole, False)
                    except:
                        pass
        except PermissionError:
            error_item = QTreeWidgetItem(parent_item)
            error_item.setText(0, "[ACCESS DENIED]")
            error_item.setForeground(0, QColor(self.colors['alert']))
        except Exception as e:
            print(f"Load folder error: {e}")

    def on_item_clicked(self, item, column):
        path = item.data(0, Qt.UserRole)
        is_dir = item.data(1, Qt.UserRole)

        if not path:
            return

        self.current_selected = path

        if is_dir:
            self.console.append(f">> OPENED DIRECTORY: {os.path.basename(path)}")
        else:
            try:
                stat = os.stat(path)
                ext = Path(path).suffix.lower()
                file_type = self.get_file_type_name(ext)

                info = (
                    f"<b style='color:{self.colors['primary']};'>FILE DETAILS</b><br><br>"
                    f"<b>Name:</b> {os.path.basename(path)}<br>"
                    f"<b>Type:</b> {file_type}<br>"
                    f"<b>Size:</b> {self.format_size(stat.st_size)}<br>"
                    f"<b>Created:</b> {time.ctime(stat.st_ctime)}<br>"
                    f"<b>Modified:</b> {time.ctime(stat.st_mtime)}<br>"
                    f"<b>Path:</b> {path}<br><br>"
                    f"<b>Status:</b> <span style='color:{self.colors['warn']};'>CLASSIFIED // EYES ONLY</span>"
                )

                if ext in ['.txt', '.md', '.json', '.xml', '.html', '.css', '.js', '.py']:
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            preview = f.read(500)
                        info += f"<br><br><b>Preview:</b><br><pre style='color:{self.colors['secondary']};'>{preview[:300]}</pre>"
                    except:
                        pass

                self.console.append(f">> SELECTED: {os.path.basename(path)} | {file_type} | {self.format_size(stat.st_size)}")
            except Exception as e:
                pass

    def get_file_type_name(self, ext):
        types = {
            '.jpg': 'IMAGE', '.jpeg': 'IMAGE', '.png': 'IMAGE', '.gif': 'IMAGE',
            '.bmp': 'IMAGE', '.tiff': 'IMAGE', '.webp': 'IMAGE',
            '.mp4': 'VIDEO', '.avi': 'VIDEO', '.mkv': 'VIDEO', '.mov': 'VIDEO',
            '.wmv': 'VIDEO', '.flv': 'VIDEO',
            '.pdf': 'DOCUMENT', '.doc': 'DOCUMENT', '.docx': 'DOCUMENT',
            '.xls': 'SPREADSHEET', '.xlsx': 'SPREADSHEET', '.csv': 'DATA',
            '.ppt': 'PRESENTATION', '.pptx': 'PRESENTATION',
            '.txt': 'TEXT', '.md': 'TEXT', '.json': 'CODE', '.xml': 'CODE',
            '.html': 'CODE', '.css': 'CODE', '.js': 'CODE', '.py': 'CODE',
            '.cpp': 'CODE', '.c': 'CODE', '.java': 'CODE',
            '.exe': 'PROGRAM', '.dll': 'SYSTEM', '.bat': 'SCRIPT',
            '.zip': 'ARCHIVE', '.rar': 'ARCHIVE', '.7z': 'ARCHIVE',
            '.tar': 'ARCHIVE', '.gz': 'ARCHIVE',
            '.mp3': 'AUDIO', '.wav': 'AUDIO', '.flac': 'AUDIO',
            '.iso': 'DISC_IMAGE', '.dmg': 'DISC_IMAGE'
        }
        return types.get(ext, 'UNKNOWN')

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    # ============================================
    # FILE OPERATIONS
    # ============================================
    def get_selected_path(self):
        items = self.tree.selectedItems()
        if items:
            return items[0].data(0, Qt.UserRole)
        return None

    def copy_selected(self):
        path = self.get_selected_path()
        if path:
            FileOperations.copy_to_clipboard(path, 'copy')
            self.clipboard_label.setText(f"Clipboard: COPY {os.path.basename(path)}")
            self.console.append(f">> COPIED: {os.path.basename(path)}")
            self.play_sound("complete")

    def cut_selected(self):
        path = self.get_selected_path()
        if path:
            FileOperations.copy_to_clipboard(path, 'cut')
            self.clipboard_label.setText(f"Clipboard: CUT {os.path.basename(path)}")
            self.console.append(f">> CUT: {os.path.basename(path)}")
            self.play_sound("complete")

    def paste_selected(self):
        if not self.current_path:
            return
        success, msg = FileOperations.paste_from_clipboard(self.current_path)
        if success:
            self.clipboard_label.setText("Clipboard: Empty")
            self.refresh_tree()
            self.console.append(f">> PASTED to {self.current_path}")
            self.play_sound("complete")
        else:
            QMessageBox.warning(self, "Paste Failed", msg)

    def delete_selected(self):
        path = self.get_selected_path()
        if not path:
            return
        if self.config.get("confirm_delete", True):
            reply = QMessageBox.question(
                self, "CONFIRM DELETION",
                f"<span style='color:{self.colors['alert']};'>Delete {os.path.basename(path)}?</span>",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        success, msg = FileOperations.delete_file(path)
        if success:
            self.refresh_tree()
            self.console.append(f">> DELETED: {os.path.basename(path)}")
            self.play_sound("alert")
        else:
            QMessageBox.warning(self, "Delete Failed", msg)

    def rename_selected(self):
        path = self.get_selected_path()
        if not path:
            return
        old_name = os.path.basename(path)
        new_name, ok = QInputDialog.getText(self, "RENAME FILE", f"New name for {old_name}:", QLineEdit.Normal, old_name)
        if ok and new_name and new_name != old_name:
            success, result = FileOperations.rename_file(path, new_name)
            if success:
                self.refresh_tree()
                self.console.append(f">> RENAMED: {old_name} -> {new_name}")
                self.play_sound("complete")
            else:
                QMessageBox.warning(self, "Rename Failed", result)

    def create_new_folder(self):
        if not self.current_path:
            return
        name, ok = QInputDialog.getText(self, "NEW FOLDER", "Folder name:", QLineEdit.Normal, "NEW_FOLDER")
        if ok and name:
            success, result = FileOperations.create_folder(self.current_path, name)
            if success:
                self.refresh_tree()
                self.console.append(f">> CREATED FOLDER: {name}")
                self.play_sound("complete")
            else:
                QMessageBox.warning(self, "Create Failed", result)

    def refresh_tree(self):
        if self.current_path and os.path.exists(self.current_path):
            self.tree.clear()
            self.tree_items.clear()
            self.load_folder_contents(self.tree, self.current_path)

    def show_context_menu(self, position):
        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{ background: {self.colors['panel']}; color: {self.colors['primary']}; border: 1px solid {self.colors['primary']}; }}
            QMenu::item {{ padding: 8px 25px; font-family: Consolas; }}
            QMenu::item:selected {{ background: {self.colors['selected']}; }}
        """)
        path = self.get_selected_path()
        if path:
            menu.addAction("📋 Copy", self.copy_selected)
            menu.addAction("✂️ Cut", self.cut_selected)
            menu.addSeparator()
            menu.addAction("🗑️ Delete", self.delete_selected)
            menu.addAction("✏️ Rename", self.rename_selected)
            menu.addSeparator()
            menu.addAction("📁 Open in Explorer", lambda: self.open_in_explorer(path))
        menu.addAction("📎 Paste", self.paste_selected)
        menu.addSeparator()
        menu.addAction("🔄 Refresh", self.refresh_tree)
        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def open_in_explorer(self, path):
        try:
            if os.path.isdir(path):
                subprocess.Popen(f'explorer.exe "{path}"', shell=True)
            else:
                subprocess.Popen(f'explorer.exe /select,"{path}"', shell=True)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot open: {e}")

    # ============================================
    # SYSTEM TRAY
    # ============================================
    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip("BIN V7.4 - Running")
        tray_menu = QMenu()
        show_action = QAction("Show Terminal", self)
        show_action.triggered.connect(self.show_and_raise)
        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        startup_action = QAction("Auto-start with Windows", self)
        startup_action.setCheckable(True)
        startup_action.setChecked(self.config.get("auto_startup", False))
        startup_action.triggered.connect(self.toggle_startup)
        tray_menu.addAction(startup_action)
        sound_action = QAction("Sound Effects", self)
        sound_action.setCheckable(True)
        sound_action.setChecked(self.config.get("sound_enabled", True))
        sound_action.triggered.connect(self.toggle_sound)
        tray_menu.addAction(sound_action)
        hidden_action = QAction("Show Hidden Files", self)
        hidden_action.setCheckable(True)
        hidden_action.setChecked(self.config.get("show_hidden", False))
        hidden_action.triggered.connect(self.toggle_hidden)
        tray_menu.addAction(hidden_action)
        tray_menu.addSeparator()
        quit_action = QAction("Terminate", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_and_raise()

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()
        if not self.isFullScreen():
            self.showFullScreen()

    def toggle_startup(self, checked):
        self.config["auto_startup"] = checked
        save_config(self.config)
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        if checked:
            exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
            winreg.SetValueEx(key, "BIN_V73", 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, "BIN_V73")
            except:
                pass
        winreg.CloseKey(key)

    def toggle_sound(self, checked):
        self.config["sound_enabled"] = checked
        save_config(self.config)

    def toggle_hidden(self, checked):
        self.config["show_hidden"] = checked
        save_config(self.config)
        self.refresh_tree()

    def play_sound(self, sound_type):
        if not self.config.get("sound_enabled", True):
            return
        try:
            if sound_type == "detect":
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            elif sound_type == "complete":
                winsound.MessageBeep(winsound.MB_OK)
            elif sound_type == "alert":
                winsound.MessageBeep(winsound.MB_ICONHAND)
        except:
            pass

    # ============================================
    # USB MONITOR
    # ============================================
    def setup_monitor(self):
        self.monitor = USBMonitor()
        self.monitor.usb_detected.connect(self.on_usb_inserted)
        self.monitor.usb_removed.connect(self.on_usb_removed)
        self.monitor.start()

    def on_usb_removed(self, drive_letter):
        if self.current_drive == drive_letter:
            self.current_drive = None
            self.volume_name = None
            self.current_path = None
            if self.live_scanner:
                self.live_scanner.stop()
                self.live_scanner = None
            if hasattr(self, 'anim_timer'):
                self.anim_timer.stop()
            self.show_screen("empty")
            self.status_label.setText("● CONNECTION LOST")
            self.status_label.setStyleSheet(f"color: {self.colors['alert']};")
            self.play_sound("alert")
            QTimer.singleShot(3000, lambda: self.show_screen("waiting"))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.hide()
                self.tray.showMessage("BIN V7.4", "Running in background.", QSystemTrayIcon.Information, 2000)
        elif event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_F5:
            self.refresh_tree()
        elif event.key() == Qt.Key_Delete:
            self.delete_selected()
        elif event.key() == Qt.Key_C and event.modifiers() == Qt.ControlModifier:
            self.copy_selected()
        elif event.key() == Qt.Key_X and event.modifiers() == Qt.ControlModifier:
            self.cut_selected()
        elif event.key() == Qt.Key_V and event.modifiers() == Qt.ControlModifier:
            self.paste_selected()

    def quit_app(self):
        if self.live_scanner:
            self.live_scanner.stop()
        self.monitor.stop()
        self.tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("BIN V7.4", "Minimized to system tray.", QSystemTrayIcon.Information, 2000)

# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    font = QFont("Consolas", 10)
    app.setFont(font)
    app.setStyleSheet("""
        QMainWindow { background: #0a0a14; }
        QWidget { font-family: Consolas, monospace; }
        QToolTip { background: #11111f; color: #00ffaa; border: 1px solid #00ffaa; padding: 5px; }
    """)
    window = BIN_V73()
    sys.exit(app.exec_())