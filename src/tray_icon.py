"""
System tray icon for Claude Code Notch.
Displays current activity status and provides menu access.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PySide6.QtCore import Qt, QTimer
from state_manager import StateManager, NotchConfig

logger = logging.getLogger(__name__)


class ClaudeNotchTray(QSystemTrayIcon):
    """System tray icon that shows Claude Code activity."""

    def __init__(self, state_manager: StateManager, user_settings=None, parent=None):
        """Initialize tray icon."""
        super().__init__(parent)

        self.state_manager = state_manager
        self.config = state_manager.config
        self.user_settings = user_settings
        self.overlay_window = None
        self._settings_dialog = None
        self._last_icon_color = None
        self._last_icon_text = None
        self._last_tooltip = None

        # Create initial icon
        self._update_icon()

        # Create menu
        self._create_menu()

        # Connect to state manager signals
        self.state_manager.activity_changed.connect(self._on_activity_changed)
        self.state_manager.session_updated.connect(self._on_session_updated)
        self.state_manager.notification_received.connect(self._on_notification)

        # Connect user settings
        if self.user_settings:
            self.user_settings.settings_changed.connect(self._on_setting_changed)

        # Set tooltip
        self.setToolTip("Claude Code - Idle")

        # Connect double-click to show overlay
        self.activated.connect(self._on_activated)

        # Timer for periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._periodic_update)
        self.update_timer.start(1000)  # Update every second

        # Show tray icon
        self.show()

        logger.info("System tray icon initialized")

    def _create_menu(self):
        """Create context menu."""
        menu = QMenu()

        # Show/Hide Overlay
        self.show_overlay_action = QAction("Show Overlay", menu)
        self.show_overlay_action.triggered.connect(self._toggle_overlay)
        menu.addAction(self.show_overlay_action)

        # Reset Position
        reset_pos_action = QAction("Reset Position", menu)
        reset_pos_action.triggered.connect(self._reset_overlay_position)
        menu.addAction(reset_pos_action)

        menu.addSeparator()

        # Settings
        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self._show_settings)
        menu.addAction(settings_action)

        # Setup Hooks
        setup_action = QAction("Setup Hooks", menu)
        setup_action.triggered.connect(self._run_setup)
        menu.addAction(setup_action)

        menu.addSeparator()

        # About
        about_action = QAction("About", menu)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self.setContextMenu(menu)

    def _create_icon(self, color: tuple = (249, 115, 22), text: str = "") -> QIcon:
        """
        Create a colored icon for the tray.

        Args:
            color: RGB tuple for icon color
            text: Optional text to display on icon

        Returns:
            QIcon object
        """
        # Create a 64x64 pixmap
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw circle
        painter.setBrush(QColor(*color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, 56, 56)

        # Draw text if provided
        if text:
            painter.setPen(QColor(255, 255, 255))
            font = QFont()
            font.setPixelSize(24)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, text)

        painter.end()

        return QIcon(pixmap)

    def _update_icon(self):
        """Update tray icon based on current activity."""
        session = self.state_manager.get_current_session()

        show_letter = True
        if self.user_settings:
            show_letter = self.user_settings.get("show_category_letter")

        if not session or not session.active_tool:
            # Idle - gray
            color = self.config.get_color_rgb('slate')
            text = ""
            tooltip = "Claude Code - Idle"
        else:
            # Active - use tool color
            tool = session.active_tool
            color = self.config.get_color_rgb(tool.color)

            # Use first letter of category as text (if enabled)
            text = (tool.category[0].upper() if tool.category else "") if show_letter else ""

            # Build tooltip
            tooltip = f"Claude Code - {tool.display_name}"
            if session.project_name:
                tooltip += f"\n{session.project_name}"
            if session.context_percent > 0:
                tooltip += f"\nContext: {session.context_percent:.1f}%"

        # Skip icon rebuild if nothing changed
        if color == self._last_icon_color and text == self._last_icon_text and tooltip == self._last_tooltip:
            return
        self._last_icon_color = color
        self._last_icon_text = text
        self._last_tooltip = tooltip

        icon = self._create_icon(color, text)
        self.setIcon(icon)
        self.setToolTip(tooltip)

    def _on_activity_changed(self):
        """Handle activity change signal."""
        self._update_icon()

    def _on_session_updated(self, session_id: str):
        """Handle session update signal."""
        self._update_icon()

    def _on_setting_changed(self, key: str):
        """React to user setting changes."""
        if key == "show_category_letter":
            self._update_icon()

    def _on_notification(self, session_id: str, message: str):
        """Show tray balloon for a Notification event."""
        self.showMessage(
            "Claude Code",
            message,
            QSystemTrayIcon.Information,
            5000
        )

    def _periodic_update(self):
        """Periodic update (cleanup, etc.)."""
        # Cleanup stale sessions
        self.state_manager.cleanup_stale_sessions()

        # Update icon (in case something changed)
        self._update_icon()

    def _on_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.DoubleClick:
            self._toggle_overlay()

    def _toggle_overlay(self):
        """Toggle overlay window visibility."""
        if self.overlay_window is None:
            # Create overlay window (lazy load)
            from overlay_window import ClaudeNotchOverlay
            self.overlay_window = ClaudeNotchOverlay(self.state_manager, user_settings=self.user_settings)

        if self.overlay_window.isVisible():
            self.overlay_window.hide()
            self.show_overlay_action.setText("Show Overlay")
        else:
            self.overlay_window.show()
            self.show_overlay_action.setText("Hide Overlay")

    def _reset_overlay_position(self):
        """Reset overlay to configured screen corner."""
        if self.overlay_window:
            self.overlay_window.reset_position()

    def _show_settings(self):
        """Show settings dialog."""
        if self._settings_dialog is None:
            from settings_dialog import SettingsDialog
            self._settings_dialog = SettingsDialog(self.user_settings)
        if self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
        else:
            self._settings_dialog.show()

    def _run_setup(self):
        """Run hook setup."""
        self.showMessage(
            "Setup",
            "Opening setup wizard...",
            QSystemTrayIcon.Information,
            2000
        )

        try:
            from setup_manager import SetupManager
            setup = SetupManager()
            success = setup.install_hooks()

            if success:
                self.showMessage(
                    "Setup Complete",
                    "Claude Code hooks installed successfully!",
                    QSystemTrayIcon.Information,
                    3000
                )
            else:
                self.showMessage(
                    "Setup Failed",
                    "Failed to install hooks. Check logs for details.",
                    QSystemTrayIcon.Warning,
                    3000
                )
        except Exception as e:
            logger.error(f"Setup error: {e}")
            self.showMessage(
                "Setup Error",
                f"Error: {str(e)}",
                QSystemTrayIcon.Critical,
                3000
            )

    def _show_about(self):
        """Show about message."""
        self.showMessage(
            "Claude Code Notch for Windows",
            "Version 1.0.0\n\nA Windows companion app for Claude Code CLI.\n\nDisplays real-time AI activity.",
            QSystemTrayIcon.Information,
            5000
        )

    def _quit_app(self):
        """Quit the application."""
        logger.info("Quitting application")

        # Hide overlay if visible
        if self.overlay_window:
            self.overlay_window.close()

        # Quit app
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()

    def set_overlay_window(self, window):
        """Set the overlay window reference."""
        self.overlay_window = window
