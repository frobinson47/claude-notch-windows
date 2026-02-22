"""
Dark-themed settings dialog for Claude Code Notch.
Non-modal, frameless dialog with live-updating preferences.
"""

import logging
import threading
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QSpinBox, QCheckBox, QComboBox, QSlider,
    QPushButton, QGroupBox, QFormLayout, QSizePolicy, QLineEdit,
    QPlainTextEdit,
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPainter, QColor, QBrush, QPainterPath, QFont, QGuiApplication
from themes import get_theme, get_theme_names, generate_dialog_stylesheet
from webhook_dispatcher import WebhookDispatcher

logger = logging.getLogger(__name__)



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
        self.setMaximumSize(560, 680)
        theme = get_theme(self.user_settings.get("theme"))
        self.setStyleSheet(generate_dialog_stylesheet(theme))

        self._build_ui()
        self.user_settings.settings_changed.connect(self._on_setting_changed)

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
        self.tabs.addTab(self._build_stats_tab(), "Stats")
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

        # Global hotkey
        self.hotkey_edit = QLineEdit()
        self.hotkey_edit.setPlaceholderText("e.g., ctrl+shift+n")
        self.hotkey_edit.setText(self.user_settings.get("global_hotkey"))
        self.hotkey_edit.editingFinished.connect(self._on_hotkey_changed)
        hotkey_note = QLabel("Leave empty to disable. Restart may be required.")
        hotkey_note.setStyleSheet("color: #888; font-size: 11px;")
        hotkey_layout = QVBoxLayout()
        hotkey_layout.setSpacing(2)
        hotkey_layout.addWidget(self.hotkey_edit)
        hotkey_layout.addWidget(hotkey_note)
        form.addRow("Global hotkey:", hotkey_layout)

        # Click-to-focus
        self.click_focus_cb = QCheckBox("Click session card to focus terminal")
        self.click_focus_cb.setChecked(self.user_settings.get("click_to_focus"))
        self.click_focus_cb.toggled.connect(lambda v: self.user_settings.set("click_to_focus", v))
        click_focus_note = QLabel("When enabled, clicking a session card brings its terminal to the foreground")
        click_focus_note.setStyleSheet("color: #888; font-size: 11px;")
        click_focus_note.setWordWrap(True)
        click_layout = QVBoxLayout()
        click_layout.setSpacing(2)
        click_layout.addWidget(self.click_focus_cb)
        click_layout.addWidget(click_focus_note)
        form.addRow("", click_layout)

        return page

    def _build_overlay_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(14)

        # Theme
        self.theme_combo = QComboBox()
        for name in get_theme_names():
            self.theme_combo.addItem(name.title(), name)
        current_theme = self.user_settings.get("theme")
        theme_idx = next((i for i, n in enumerate(get_theme_names()) if n == current_theme), 0)
        self.theme_combo.setCurrentIndex(theme_idx)
        self.theme_combo.currentIndexChanged.connect(
            lambda i: self.user_settings.set("theme", self.theme_combo.itemData(i))
        )
        form.addRow("Theme:", self.theme_combo)

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

        # F1: Target monitor
        self.monitor_combo = QComboBox()
        self._populate_monitors()
        self.monitor_combo.currentIndexChanged.connect(
            lambda i: self.user_settings.set("target_monitor", self.monitor_combo.itemData(i) or "")
        )
        form.addRow("Target monitor:", self.monitor_combo)

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

        # Mini mode
        self.mini_mode_cb = QCheckBox("Mini mode (compact single-line cards)")
        self.mini_mode_cb.setChecked(self.user_settings.get("mini_mode"))
        self.mini_mode_cb.toggled.connect(lambda v: self.user_settings.set("mini_mode", v))
        form.addRow("", self.mini_mode_cb)

        # F2: Per-project accent colors
        colors_group = QGroupBox("Project Accent Colors")
        colors_layout = QVBoxLayout(colors_group)
        self.project_colors_edit = QPlainTextEdit()
        self.project_colors_edit.setFixedHeight(80)
        self.project_colors_edit.setPlaceholderText("project_name=color_name (one per line)")
        self.project_colors_edit.setStyleSheet(
            "QPlainTextEdit { background: #2a2a2a; color: #eee; border: 1px solid #555; "
            "border-radius: 4px; padding: 4px; font-size: 12px; }"
        )
        self._load_project_colors_text()
        self.project_colors_edit.focusOutEvent = self._project_colors_focus_out
        colors_layout.addWidget(self.project_colors_edit)
        colors_note = QLabel("Available colors: cyan, purple, green, amber, orange, red, violet, blue, slate")
        colors_note.setStyleSheet("color: #888; font-size: 11px;")
        colors_note.setWordWrap(True)
        colors_layout.addWidget(colors_note)
        form.addRow(colors_group)

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

        # F3: Desktop toasts
        self.toasts_cb = QCheckBox("Enable desktop toast notifications")
        self.toasts_cb.setChecked(self.user_settings.get("toasts_enabled"))
        self.toasts_cb.toggled.connect(lambda v: self.user_settings.set("toasts_enabled", v))
        form.addRow("", self.toasts_cb)

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

        # Webhook notifications
        webhook_group = QGroupBox("Webhook Notifications")
        webhook_layout = QVBoxLayout(webhook_group)

        self.webhook_cb = QCheckBox("Enable webhook notifications")
        self.webhook_cb.setChecked(self.user_settings.get("webhook_enabled"))
        self.webhook_cb.toggled.connect(lambda v: self.user_settings.set("webhook_enabled", v))
        webhook_layout.addWidget(self.webhook_cb)

        url_layout = QHBoxLayout()
        self.webhook_url_edit = QLineEdit()
        self.webhook_url_edit.setPlaceholderText("https://discord.com/api/webhooks/... or https://hooks.slack.com/...")
        self.webhook_url_edit.setText(self.user_settings.get("webhook_url"))
        self.webhook_url_edit.editingFinished.connect(self._on_webhook_url_changed)
        url_layout.addWidget(self.webhook_url_edit)

        self.webhook_test_btn = QPushButton("Test")
        self.webhook_test_btn.setFixedWidth(60)
        self.webhook_test_btn.clicked.connect(self._test_webhook)
        url_layout.addWidget(self.webhook_test_btn)
        webhook_layout.addLayout(url_layout)

        self.webhook_status_label = QLabel("")
        self.webhook_status_label.setStyleSheet("color: #888; font-size: 11px;")
        self.webhook_status_label.setWordWrap(True)
        webhook_layout.addWidget(self.webhook_status_label)

        webhook_note = QLabel("Sends event summaries (errors, attention, session end) to Discord or Slack")
        webhook_note.setStyleSheet("color: #888; font-size: 11px;")
        webhook_note.setWordWrap(True)
        webhook_layout.addWidget(webhook_note)

        form.addRow(webhook_group)

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

    def _build_stats_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Load stats
        from session_stats import SessionStats
        stats = SessionStats()
        data = stats.get_stats()

        # Summary group
        summary_group = QGroupBox("Summary")
        summary_form = QFormLayout(summary_group)
        summary_form.addRow("Sessions tracked:", QLabel(str(data.get("session_count", 0))))
        summary_form.addRow("Total tool uses:", QLabel(str(data.get("total_tool_uses", 0))))

        first = data.get("first_recorded")
        if first and first > 0:
            from datetime import datetime
            since_str = datetime.fromtimestamp(first).strftime("%Y-%m-%d")
            summary_form.addRow("Tracking since:", QLabel(since_str))
        layout.addWidget(summary_group)

        # Tool counts group (top 10)
        tool_group = QGroupBox("Tool Usage (top 10)")
        tool_layout = QVBoxLayout(tool_group)
        tool_counts = data.get("tool_counts", {})
        sorted_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        if sorted_tools:
            for tool_name, count in sorted_tools:
                row = QHBoxLayout()
                name_label = QLabel(tool_name)
                name_label.setStyleSheet("color: #ddd; font-size: 12px;")
                count_label = QLabel(str(count))
                count_label.setStyleSheet("color: #4a9eff; font-size: 12px; font-weight: bold;")
                count_label.setAlignment(Qt.AlignRight)
                row.addWidget(name_label)
                row.addStretch()
                row.addWidget(count_label)
                tool_layout.addLayout(row)
        else:
            empty = QLabel("No data yet")
            empty.setStyleSheet("color: #888; font-size: 12px;")
            tool_layout.addWidget(empty)
        layout.addWidget(tool_group)

        # Category time group
        cat_group = QGroupBox("Time by Category")
        cat_layout = QVBoxLayout(cat_group)
        cat_seconds = data.get("category_seconds", {})
        sorted_cats = sorted(cat_seconds.items(), key=lambda x: x[1], reverse=True)
        if sorted_cats:
            for cat_name, seconds in sorted_cats:
                row = QHBoxLayout()
                name_label = QLabel(cat_name.title())
                name_label.setStyleSheet("color: #ddd; font-size: 12px;")
                if seconds >= 3600:
                    time_str = f"{seconds/3600:.1f}h"
                elif seconds >= 60:
                    time_str = f"{seconds/60:.1f}m"
                else:
                    time_str = f"{seconds:.0f}s"
                time_label = QLabel(time_str)
                time_label.setStyleSheet("color: #4a9eff; font-size: 12px; font-weight: bold;")
                time_label.setAlignment(Qt.AlignRight)
                row.addWidget(name_label)
                row.addStretch()
                row.addWidget(time_label)
                cat_layout.addLayout(row)
        else:
            empty = QLabel("No data yet")
            empty.setStyleSheet("color: #888; font-size: 12px;")
            cat_layout.addWidget(empty)
        layout.addWidget(cat_group)

        layout.addStretch()
        return page

    # ── Callbacks ────────────────────────────────────────────────

    def _populate_monitors(self):
        """Populate monitor combo from available screens."""
        self.monitor_combo.blockSignals(True)
        self.monitor_combo.clear()
        self.monitor_combo.addItem("Primary Screen", "")
        current = self.user_settings.get("target_monitor")
        selected_idx = 0
        for screen in QGuiApplication.screens():
            name = screen.name()
            geo = screen.geometry()
            label = f"{name} ({geo.width()}x{geo.height()})"
            self.monitor_combo.addItem(label, name)
            if name == current:
                selected_idx = self.monitor_combo.count() - 1
        self.monitor_combo.setCurrentIndex(selected_idx)
        self.monitor_combo.blockSignals(False)

    def _load_project_colors_text(self):
        """Load project_colors dict into the text editor."""
        colors = self.user_settings.get("project_colors")
        lines = [f"{k}={v}" for k, v in sorted(colors.items())]
        self.project_colors_edit.setPlainText("\n".join(lines))

    def _project_colors_focus_out(self, event):
        """Parse and save project colors when the text editor loses focus."""
        QPlainTextEdit.focusOutEvent(self.project_colors_edit, event)
        self._save_project_colors()

    def _save_project_colors(self):
        """Parse text into dict and save."""
        text = self.project_colors_edit.toPlainText()
        colors = {}
        for line in text.strip().splitlines():
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and value:
                colors[key] = value
        self.user_settings.set("project_colors", colors)

    def _on_setting_changed(self, key: str):
        if key == "theme":
            theme = get_theme(self.user_settings.get("theme"))
            self.setStyleSheet(generate_dialog_stylesheet(theme))
            self.update()  # repaint background

    def _on_opacity_changed(self, value: int):
        self.opacity_label.setText(f"{round(value / 255 * 100)}%")
        self.user_settings.set("background_opacity", value)

    def _on_speed_changed(self, value: int):
        mult = round(value / 100, 2)
        self.speed_label.setText(f"{mult:.2f}x")
        self.user_settings.set("animation_speed_multiplier", mult)

    def _on_hotkey_changed(self):
        value = self.hotkey_edit.text().strip().lower()
        self.hotkey_edit.setText(value)
        self.user_settings.set("global_hotkey", value)

    def _on_startup_toggled(self, checked: bool):
        self.user_settings.set("launch_on_startup", checked)
        self.user_settings.set_startup_enabled(checked)

    def _on_webhook_url_changed(self):
        url = self.webhook_url_edit.text().strip()
        self.webhook_url_edit.setText(url)
        self.user_settings.set("webhook_url", url)

    def _test_webhook(self):
        url = self.webhook_url_edit.text().strip()
        if not url:
            self.webhook_status_label.setText("Enter a webhook URL first")
            self.webhook_status_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
            return
        self.webhook_test_btn.setEnabled(False)
        self.webhook_status_label.setText("Testing...")
        self.webhook_status_label.setStyleSheet("color: #888; font-size: 11px;")

        def _run_test():
            dispatcher = WebhookDispatcher()
            ok, msg = dispatcher.send_test(url)
            # Update UI from main thread
            self.webhook_test_btn.setEnabled(True)
            if ok:
                self.webhook_status_label.setText("Test sent successfully!")
                self.webhook_status_label.setStyleSheet("color: #4a9; font-size: 11px;")
            else:
                self.webhook_status_label.setText(f"Failed: {msg}")
                self.webhook_status_label.setStyleSheet("color: #e74c3c; font-size: 11px;")

        threading.Thread(target=_run_test, daemon=True).start()

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
        self.toasts_cb.setChecked(self.user_settings.get("toasts_enabled"))
        self.mini_mode_cb.setChecked(self.user_settings.get("mini_mode"))
        self.click_focus_cb.setChecked(self.user_settings.get("click_to_focus"))
        theme_idx = next((i for i, n in enumerate(get_theme_names()) if n == self.user_settings.get("theme")), 0)
        self.theme_combo.setCurrentIndex(theme_idx)
        self.hotkey_edit.setText(self.user_settings.get("global_hotkey"))
        self._populate_monitors()
        self._load_project_colors_text()
        self.webhook_cb.setChecked(self.user_settings.get("webhook_enabled"))
        self.webhook_url_edit.setText(self.user_settings.get("webhook_url"))

    # ── Painting & drag ──────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        theme = get_theme(self.user_settings.get("theme"))
        bg_rgb = theme["bg"]
        bg = QColor(*bg_rgb, 240)
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
