"""
Dark-themed settings dialog for Claude Code Notch.
Non-modal, frameless dialog with live-updating preferences.
"""

import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSpinBox, QCheckBox, QComboBox, QSlider,
    QPushButton, QGroupBox, QFormLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QColor, QBrush, QPainterPath, QFont

logger = logging.getLogger(__name__)

# Shared dark stylesheet for all widgets inside the dialog
_DARK_STYLE = """
QTabWidget::pane {
    border: 1px solid #444;
    background: transparent;
    border-radius: 6px;
}
QTabBar::tab {
    background: #2a2a2a;
    color: #ccc;
    padding: 8px 18px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background: #3a3a3a;
    color: #fff;
}
QTabBar::tab:hover {
    background: #333;
}
QLabel {
    color: #ddd;
    font-size: 13px;
}
QSpinBox, QComboBox {
    background: #2a2a2a;
    color: #eee;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 80px;
}
QSpinBox::up-button, QSpinBox::down-button {
    background: #333;
    border: none;
    width: 16px;
}
QSpinBox::up-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 5px solid #aaa; }
QSpinBox::down-arrow { image: none; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #aaa; }
QCheckBox {
    color: #ddd;
    font-size: 13px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 3px;
    border: 1px solid #666;
    background: #2a2a2a;
}
QCheckBox::indicator:checked {
    background: #4a9eff;
    border-color: #4a9eff;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #333;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #4a9eff;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: #4a9eff;
    border-radius: 3px;
}
QPushButton {
    background: #333;
    color: #ddd;
    border: 1px solid #555;
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background: #444;
}
QPushButton:pressed {
    background: #222;
}
QGroupBox {
    color: #aaa;
    border: 1px solid #444;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 16px;
    font-size: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #aaa;
}
QComboBox QAbstractItemView {
    background: #2a2a2a;
    color: #eee;
    selection-background-color: #4a9eff;
    border: 1px solid #555;
}
"""


class SettingsDialog(QDialog):
    """Dark-themed, frameless settings dialog."""

    def __init__(self, user_settings, parent=None):
        super().__init__(parent)
        self.user_settings = user_settings
        self._drag_pos = QPoint()

        # Frameless, translucent, tool window
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(480, 420)
        self.setMaximumSize(560, 580)
        self.setStyleSheet(_DARK_STYLE)

        self._build_ui()

    # ── UI construction ──────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(0)

        # Custom title bar
        title_bar = QHBoxLayout()
        title_label = QLabel("Settings")
        title_label.setStyleSheet("color: #fff; font-size: 16px; font-weight: bold;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()
        close_btn = QPushButton("\u2715")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #aaa; font-size: 16px; border: none; border-radius: 14px; }"
            "QPushButton:hover { background: #c0392b; color: #fff; }"
        )
        close_btn.clicked.connect(self.close)
        title_bar.addWidget(close_btn)
        root.addLayout(title_bar)

        root.addSpacing(8)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_behavior_tab(), "Behavior")
        self.tabs.addTab(self._build_overlay_tab(), "Overlay")
        self.tabs.addTab(self._build_tray_tab(), "Tray")
        self.tabs.addTab(self._build_notifications_tab(), "Notifications")
        self.tabs.addTab(self._build_hooks_tab(), "Hooks")
        self.tabs.addTab(self._build_animations_tab(), "Animations")
        root.addWidget(self.tabs, 1)

        root.addSpacing(10)

        # Bottom bar
        bottom = QHBoxLayout()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        bottom.addWidget(reset_btn)
        bottom.addStretch()
        close_btn2 = QPushButton("Close")
        close_btn2.clicked.connect(self.close)
        bottom.addWidget(close_btn2)
        root.addLayout(bottom)

    # ── Tab builders ─────────────────────────────────────────────

    def _build_behavior_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(14)

        # Idle timeout
        self.idle_spin = QSpinBox()
        self.idle_spin.setRange(5, 120)
        self.idle_spin.setSuffix(" sec")
        self.idle_spin.setValue(self.user_settings.get("idle_timeout"))
        self.idle_spin.valueChanged.connect(lambda v: self.user_settings.set("idle_timeout", v))
        form.addRow("Idle timeout:", self.idle_spin)

        # Activity (stale) timeout
        self.stale_spin = QSpinBox()
        self.stale_spin.setRange(10, 300)
        self.stale_spin.setSuffix(" sec")
        self.stale_spin.setValue(self.user_settings.get("activity_timeout"))
        self.stale_spin.valueChanged.connect(lambda v: self.user_settings.set("activity_timeout", v))
        form.addRow("Stale timeout:", self.stale_spin)

        # Server port
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(self.user_settings.get("server_port"))
        self.port_spin.valueChanged.connect(lambda v: self.user_settings.set("server_port", v))
        port_note = QLabel("Restart required after changing port")
        port_note.setStyleSheet("color: #888; font-size: 11px;")
        port_layout = QVBoxLayout()
        port_layout.setSpacing(2)
        port_layout.addWidget(self.port_spin)
        port_layout.addWidget(port_note)
        form.addRow("Server port:", port_layout)

        # Launch on startup
        self.startup_cb = QCheckBox("Launch on Windows startup")
        self.startup_cb.setChecked(self.user_settings.get("launch_on_startup"))
        self.startup_cb.toggled.connect(self._on_startup_toggled)
        form.addRow("", self.startup_cb)

        return page

    def _build_overlay_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(14)

        # Screen position
        self.position_combo = QComboBox()
        positions = [
            ("Top Right", "top-right"),
            ("Top Left", "top-left"),
            ("Bottom Right", "bottom-right"),
            ("Bottom Left", "bottom-left"),
        ]
        for label, value in positions:
            self.position_combo.addItem(label, value)
        current_pos = self.user_settings.get("screen_position")
        idx = next((i for i, (_, v) in enumerate(positions) if v == current_pos), 0)
        self.position_combo.setCurrentIndex(idx)
        self.position_combo.currentIndexChanged.connect(
            lambda i: self.user_settings.set("screen_position", self.position_combo.itemData(i))
        )
        form.addRow("Screen position:", self.position_combo)

        # Background opacity
        opacity_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setValue(self.user_settings.get("background_opacity"))
        self.opacity_label = QLabel(f"{round(self.opacity_slider.value() / 255 * 100)}%")
        self.opacity_label.setFixedWidth(40)
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        form.addRow("Background opacity:", opacity_layout)

        # Auto-hide
        self.auto_hide_cb = QCheckBox("Auto-hide overlay when idle")
        self.auto_hide_cb.setChecked(self.user_settings.get("auto_hide"))
        self.auto_hide_cb.toggled.connect(lambda v: self.user_settings.set("auto_hide", v))
        form.addRow("", self.auto_hide_cb)

        return page

    def _build_tray_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(14)

        self.letter_cb = QCheckBox("Show category letter on tray icon")
        self.letter_cb.setChecked(self.user_settings.get("show_category_letter"))
        self.letter_cb.toggled.connect(lambda v: self.user_settings.set("show_category_letter", v))
        form.addRow("", self.letter_cb)

        return page

    def _build_notifications_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(14)

        # Sound cues
        self.sounds_cb = QCheckBox("Enable sound cues")
        self.sounds_cb.setChecked(self.user_settings.get("sounds_enabled"))
        self.sounds_cb.toggled.connect(lambda v: self.user_settings.set("sounds_enabled", v))
        form.addRow("", self.sounds_cb)

        # Error flash
        self.error_flash_cb = QCheckBox("Enable error flash")
        self.error_flash_cb.setChecked(self.user_settings.get("error_flash_enabled"))
        self.error_flash_cb.toggled.connect(lambda v: self.user_settings.set("error_flash_enabled", v))
        form.addRow("", self.error_flash_cb)

        # Info label
        info = QLabel(
            "Sound cues play for:\n"
            "  - Errors (Bash failures)\n"
            "  - Attention needed (user questions)\n"
            "  - Session end"
        )
        info.setStyleSheet("color: #888; font-size: 11px;")
        info.setWordWrap(True)
        form.addRow("", info)

        return page

    def _build_hooks_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Status
        self.hook_status_label = QLabel()
        self.hook_status_label.setWordWrap(True)
        layout.addWidget(self.hook_status_label)

        # Paths
        try:
            from setup_manager import SetupManager
            sm = SetupManager()
            self._setup_manager = sm
            hooks_path = str(sm.hooks_dir)
            settings_path = str(sm.settings_file)
            installed = sm.is_installed()
        except Exception:
            self._setup_manager = None
            hooks_path = "N/A"
            settings_path = "N/A"
            installed = False

        status_text = "Installed" if installed else "Not installed"
        status_color = "#4a9" if installed else "#e74c3c"
        self.hook_status_label.setText(
            f'<span style="color:{status_color}; font-weight:bold;">{status_text}</span>'
        )

        path_group = QGroupBox("Paths")
        path_form = QFormLayout(path_group)
        hooks_label = QLabel(hooks_path)
        hooks_label.setStyleSheet("color: #999; font-size: 11px;")
        hooks_label.setWordWrap(True)
        path_form.addRow("Hooks:", hooks_label)
        settings_label = QLabel(settings_path)
        settings_label.setStyleSheet("color: #999; font-size: 11px;")
        settings_label.setWordWrap(True)
        path_form.addRow("Settings:", settings_label)
        layout.addWidget(path_group)

        # Buttons
        btn_row = QHBoxLayout()
        install_btn = QPushButton("Install Hooks")
        install_btn.clicked.connect(self._install_hooks)
        btn_row.addWidget(install_btn)
        uninstall_btn = QPushButton("Uninstall Hooks")
        uninstall_btn.clicked.connect(self._uninstall_hooks)
        btn_row.addWidget(uninstall_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()
        return page

    def _build_animations_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(14)

        # Enable animations
        self.anim_cb = QCheckBox("Enable animations")
        self.anim_cb.setChecked(self.user_settings.get("animations_enabled"))
        self.anim_cb.toggled.connect(lambda v: self.user_settings.set("animations_enabled", v))
        form.addRow("", self.anim_cb)

        # Speed multiplier
        speed_layout = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(25, 300)  # 0.25x to 3.0x (*100)
        self.speed_slider.setValue(int(self.user_settings.get("animation_speed_multiplier") * 100))
        self.speed_label = QLabel(f"{self.speed_slider.value() / 100:.2f}x")
        self.speed_label.setFixedWidth(45)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        form.addRow("Speed multiplier:", speed_layout)

        return page

    # ── Callbacks ────────────────────────────────────────────────

    def _on_opacity_changed(self, value: int):
        self.opacity_label.setText(f"{round(value / 255 * 100)}%")
        self.user_settings.set("background_opacity", value)

    def _on_speed_changed(self, value: int):
        mult = round(value / 100, 2)
        self.speed_label.setText(f"{mult:.2f}x")
        self.user_settings.set("animation_speed_multiplier", mult)

    def _on_startup_toggled(self, checked: bool):
        self.user_settings.set("launch_on_startup", checked)
        self.user_settings.set_startup_enabled(checked)

    def _install_hooks(self):
        if not self._setup_manager:
            return
        ok = self._setup_manager.install_hooks()
        color = "#4a9" if ok else "#e74c3c"
        text = "Installed" if ok else "Installation failed"
        self.hook_status_label.setText(
            f'<span style="color:{color}; font-weight:bold;">{text}</span>'
        )

    def _uninstall_hooks(self):
        if not self._setup_manager:
            return
        ok = self._setup_manager.uninstall_hooks()
        color = "#e74c3c" if ok else "#4a9"
        text = "Not installed" if ok else "Uninstall failed"
        self.hook_status_label.setText(
            f'<span style="color:{color}; font-weight:bold;">{text}</span>'
        )

    def _reset_defaults(self):
        self.user_settings.reset_to_defaults()
        # Refresh all widgets
        self.idle_spin.setValue(self.user_settings.get("idle_timeout"))
        self.stale_spin.setValue(self.user_settings.get("activity_timeout"))
        self.port_spin.setValue(self.user_settings.get("server_port"))
        self.startup_cb.setChecked(self.user_settings.get("launch_on_startup"))
        idx = next(
            (i for i in range(self.position_combo.count())
             if self.position_combo.itemData(i) == self.user_settings.get("screen_position")),
            0,
        )
        self.position_combo.setCurrentIndex(idx)
        self.opacity_slider.setValue(self.user_settings.get("background_opacity"))
        self.auto_hide_cb.setChecked(self.user_settings.get("auto_hide"))
        self.letter_cb.setChecked(self.user_settings.get("show_category_letter"))
        self.anim_cb.setChecked(self.user_settings.get("animations_enabled"))
        self.speed_slider.setValue(int(self.user_settings.get("animation_speed_multiplier") * 100))
        self.sounds_cb.setChecked(self.user_settings.get("sounds_enabled"))
        self.error_flash_cb.setChecked(self.user_settings.get("error_flash_enabled"))

    # ── Painting & drag ──────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bg = QColor(20, 20, 20, 240)
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.NoPen)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 15, 15)
        painter.drawPath(path)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
