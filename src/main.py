"""
Claude Code Notch for Windows
Main application entry point.
"""

import sys
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer, QObject, Signal, Slot

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from http_server import ClaudeCodeServer
from state_manager import StateManager, NotchConfig
from user_settings import UserSettings
from tray_icon import ClaudeNotchTray
from overlay_window import ClaudeNotchOverlay
from notification_manager import NotificationManager


# Setup logging
def setup_logging():
    """Setup application logging."""
    log_dir = Path.home() / "AppData" / "Roaming" / "claude-notch-windows" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "claude-notch.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


class _EventBridge(QObject):
    """Thread-safe bridge: HTTP thread emits signal, Qt main thread handles it."""
    event_signal = Signal(str, object)  # event_type, data dict

    def __init__(self, state_manager):
        super().__init__()
        self._state_manager = state_manager
        self.event_signal.connect(self._on_event)

    @Slot(str, object)
    def _on_event(self, event_type, data):
        self._state_manager.handle_event(event_type, data)


class ClaudeNotchApp:
    """Main application controller."""

    def __init__(self):
        """Initialize application."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Starting Claude Code Notch for Windows...")

        # Create QApplication
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("Claude Code Notch")
        self.app.setQuitOnLastWindowClosed(False)  # Keep running in tray

        # Load configuration
        try:
            self.config = NotchConfig()
            self.logger.info("Configuration loaded")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)

        # Load user settings
        self.user_settings = UserSettings()
        self.logger.info("User settings loaded")

        # Create state manager
        self.state_manager = StateManager(self.config, user_settings=self.user_settings)
        self.logger.info("State manager created")

        # Create HTTP server (port from user settings)
        # Bridge marshals events from HTTP thread -> Qt main thread via signal
        server_port = self.user_settings.get("server_port")
        self._event_bridge = _EventBridge(self.state_manager)

        self.server = ClaudeCodeServer(
            port=server_port,
            event_callback=self._event_bridge.event_signal.emit,
            status_callback=self.state_manager.get_status_dict,
        )

        # Start server
        try:
            self.server.start()
            self.logger.info(f"HTTP server started on port {server_port}")
        except OSError as e:
            # errno 10048 = WSAEADDRINUSE on Windows
            if getattr(e, 'errno', None) == 10048 or "address already in use" in str(e).lower():
                self.logger.error(f"Another instance is already running (port {server_port} in use)")
            else:
                self.logger.error(f"Failed to start server: {e}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            sys.exit(1)

        # Create notification manager (sound cues + error flash)
        self.notification_manager = NotificationManager(
            self.state_manager, self.user_settings
        )
        self.logger.info("Notification manager created")

        # Create overlay window (but don't show yet)
        self.overlay = ClaudeNotchOverlay(
            self.state_manager, user_settings=self.user_settings,
            notification_manager=self.notification_manager,
        )
        self.logger.info("Overlay window created")

        # Create system tray icon
        self.tray = ClaudeNotchTray(self.state_manager, user_settings=self.user_settings)
        self.tray.set_overlay_window(self.overlay)
        self.logger.info("System tray icon created")

        self.logger.info("Application initialized successfully")

    def run(self):
        """Run the application."""
        self.logger.info("Application running")
        return self.app.exec()

    def cleanup(self):
        """Cleanup on exit."""
        self.logger.info("Cleaning up...")

        # Stop server
        if self.server:
            self.server.stop()

        # Hide overlay
        if self.overlay:
            self.overlay.hide()

        self.logger.info("Cleanup complete")


def main():
    """Main entry point."""
    # Setup logging
    logger = setup_logging()

    try:
        # Create and run app
        app = ClaudeNotchApp()
        exit_code = app.run()

        # Cleanup
        app.cleanup()

        sys.exit(exit_code)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
