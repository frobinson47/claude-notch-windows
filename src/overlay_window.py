"""
Floating overlay window that displays Claude Code activity.
Transparent, click-through window positioned at top-right of screen.
"""

import logging
import random
from typing import List, Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont
from state_manager import StateManager, SessionState

logger = logging.getLogger(__name__)


class ActivityIndicator(QWidget):
    """
    3x2 grid animation showing activity pattern.
    Mimics the macOS version's semantic animations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedSize(120, 80)  # 3 cols x 2 rows, 40x40 squares

        # Animation state
        self.lit_squares = []  # List of indices (0-5) that are currently lit
        self.color = QColor(249, 115, 22)  # Default orange
        self.opacity_value = 0.8
        self.pattern_config = None
        self.sequence_index = 0

        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_step)

    def set_pattern(self, pattern_name: str, color_rgb: tuple, config: dict):
        """
        Set the animation pattern.

        Args:
            pattern_name: Name of pattern (scan, cogitate, etc.)
            color_rgb: RGB tuple for color
            config: Pattern configuration dict
        """
        self.color = QColor(*color_rgb)
        self.pattern_config = config
        self.sequence_index = 0

        # Start animation
        interval = int(config.get('interval', 0.1) * 1000)  # Convert to ms
        if interval > 0:
            self.animation_timer.start(interval)
        else:
            self.animation_timer.stop()
            self.lit_squares = config.get('sequence', [[]])[0]

        self.update()

    def stop_animation(self):
        """Stop the animation."""
        self.animation_timer.stop()
        self.lit_squares = []
        self.update()

    def _animate_step(self):
        """Advance animation by one step."""
        if not self.pattern_config:
            return

        mode = self.pattern_config.get('mode', 'static')

        if mode == 'sequence':
            # Sequential pattern
            sequence = self.pattern_config.get('sequence', [[]])
            self.lit_squares = sequence[self.sequence_index % len(sequence)]
            self.sequence_index += 1

        elif mode == 'random':
            # Random pattern
            lit_range = self.pattern_config.get('litRange', [2, 4])
            num_lit = random.randint(lit_range[0], lit_range[1])
            self.lit_squares = random.sample(range(6), num_lit)

        elif mode == 'breathe':
            # All squares pulse together (handled via opacity)
            self.lit_squares = [0, 1, 2, 3, 4, 5]

        elif mode == 'static':
            # Static pattern
            sequence = self.pattern_config.get('sequence', [[]])
            self.lit_squares = sequence[0] if sequence else []

        self.update()

    def set_opacity(self, value: float):
        """Set opacity value (0.0 - 1.0)."""
        self.opacity_value = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event):
        """Paint the 3x2 grid."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw 6 squares (3x2 grid)
        square_size = 35
        gap = 5

        for i in range(6):
            row = i // 3
            col = i % 3

            x = col * (square_size + gap) + gap
            y = row * (square_size + gap) + gap

            # Determine if this square is lit
            is_lit = i in self.lit_squares

            if is_lit:
                # Lit square
                color = QColor(self.color)
                color.setAlphaF(self.opacity_value)
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
            else:
                # Dim square
                color = QColor(100, 100, 100, int(50 * self.opacity_value))
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)

            # Draw rounded square
            painter.drawRoundedRect(x, y, square_size, square_size, 4, 4)


class SessionCard(QWidget):
    """
    Card displaying a single session's activity.
    Shows project name, tool status, and activity indicator.
    """

    def __init__(self, session: SessionState, config, parent=None):
        super().__init__(parent)

        self.session = session
        self.config = config

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        # Activity indicator
        self.activity_indicator = ActivityIndicator()
        layout.addWidget(self.activity_indicator)

        # Text info
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)

        # Project name
        self.project_label = QLabel(self.session.display_name)
        self.project_label.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        text_layout.addWidget(self.project_label)

        # Tool/status
        self.status_label = QLabel(self._get_status_text())
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); font-size: 12px;")
        text_layout.addWidget(self.status_label)

        # Context percentage
        self.context_label = QLabel(self._get_context_text())
        self.context_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        text_layout.addWidget(self.context_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Update animation
        self.update_animation()

    def _get_status_text(self) -> str:
        """Get status text."""
        if self.session.active_tool:
            return self.session.active_tool.display_name
        return "Idle"

    def _get_context_text(self) -> str:
        """Get context percentage text."""
        if self.session.context_percent > 0:
            return f"Context: {self.session.context_percent:.1f}%"
        return ""

    def update_animation(self):
        """Update animation based on current session state."""
        if self.session.active_tool:
            tool = self.session.active_tool
            color_rgb = self.config.get_color_rgb(tool.color)
            pattern_config = self.config.get_pattern_config(tool.pattern)
            self.activity_indicator.set_pattern(tool.pattern, color_rgb, pattern_config)
        else:
            # Idle - dormant pattern
            color_rgb = self.config.get_color_rgb('slate')
            pattern_config = self.config.get_pattern_config('dormant')
            self.activity_indicator.set_pattern('dormant', color_rgb, pattern_config)

    def update_display(self):
        """Update display labels."""
        self.project_label.setText(self.session.display_name)
        self.status_label.setText(self._get_status_text())
        self.context_label.setText(self._get_context_text())
        self.update_animation()


class ClaudeNotchOverlay(QWidget):
    """
    Main overlay window.
    Transparent, frameless window showing Claude activity.
    """

    def __init__(self, state_manager: StateManager, parent=None):
        super().__init__(parent)

        self.state_manager = state_manager
        self.config = state_manager.config
        self.session_cards = {}  # session_id -> SessionCard

        # Window flags for overlay
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.X11BypassWindowManagerHint
        )

        # Transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Allow mouse events

        # Setup UI
        self._setup_ui()

        # Connect signals
        self.state_manager.activity_changed.connect(self._on_activity_changed)
        self.state_manager.session_updated.connect(self._on_session_updated)

        # Position window
        self._position_window()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._periodic_update)
        self.update_timer.start(1000)

        logger.info("Overlay window initialized")

    def _setup_ui(self):
        """Setup UI layout."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(10)

        # Set minimum size
        self.setMinimumSize(400, 100)

    def _position_window(self):
        """Position window at top-right of screen."""
        from PyQt5.QtWidgets import QDesktopWidget

        desktop = QDesktopWidget()
        screen_rect = desktop.availableGeometry()

        # Position at top-right with some padding
        padding = 20
        x = screen_rect.right() - self.width() - padding
        y = screen_rect.top() + padding

        self.move(x, y)

    def _on_activity_changed(self):
        """Handle activity change."""
        self._update_sessions()

    def _on_session_updated(self, session_id: str):
        """Handle session update."""
        self._update_sessions()

    def _update_sessions(self):
        """Update session cards based on current state."""
        # Get sessions to display
        sessions = self.state_manager.get_display_sessions()

        # Remove old cards
        for session_id in list(self.session_cards.keys()):
            if not any(s.session_id == session_id for s in sessions):
                card = self.session_cards.pop(session_id)
                self.layout.removeWidget(card)
                card.deleteLater()

        # Update or create cards
        for session in sessions:
            if session.session_id in self.session_cards:
                # Update existing card
                card = self.session_cards[session.session_id]
                card.session = session
                card.update_display()
            else:
                # Create new card
                card = SessionCard(session, self.config)
                self.session_cards[session.session_id] = card
                self.layout.addWidget(card)

        # Show/hide window based on activity
        if sessions and not self.state_manager.is_idle:
            if not self.isVisible():
                self.show()
        else:
            if self.isVisible():
                self.hide()

        # Adjust window size
        self.adjustSize()
        self._position_window()

    def _periodic_update(self):
        """Periodic update."""
        # Update all session cards
        for card in self.session_cards.values():
            card.update_display()

    def paintEvent(self, event):
        """Paint semi-transparent background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw rounded rectangle background
        bg_color = QColor(20, 20, 20, 220)  # Dark semi-transparent
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 15, 15)
        painter.drawPath(path)

    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
