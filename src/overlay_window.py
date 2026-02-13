"""
Floating overlay window that displays Claude Code activity.
Transparent, click-through window positioned at top-right of screen.
"""

import logging
import math
import random
import time
from typing import List, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar
from PySide6.QtCore import Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QGuiApplication
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

    def set_pattern(self, pattern_name: str, color_rgb: tuple, config: dict,
                    speed_multiplier: float = 1.0, animations_enabled: bool = True,
                    attention_config: dict = None):
        """
        Set the animation pattern.

        Args:
            pattern_name: Name of pattern (scan, cogitate, etc.)
            color_rgb: RGB tuple for color
            config: Pattern configuration dict
            speed_multiplier: Speed multiplier for animation interval
            animations_enabled: Whether animations are enabled
            attention_config: Attention level config with opacity range
        """
        self.color = QColor(*color_rgb)
        self.pattern_config = config
        self.sequence_index = 0

        # Set opacity from attention level (fixed midpoint of range)
        if attention_config:
            opacity_range = attention_config.get('opacity', [0.6, 0.85])
            self.opacity_value = (opacity_range[0] + opacity_range[1]) / 2
        else:
            self.opacity_value = 0.8

        if not animations_enabled:
            # Show static first frame
            self.animation_timer.stop()
            sequence = config.get('sequence', [[]])
            self.lit_squares = sequence[0] if sequence else []
            self.update()
            return

        # Start animation with speed multiplier applied
        base_interval = config.get('interval', 0.1) * 1000  # Convert to ms
        interval = max(10, int(base_interval / speed_multiplier))
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
            # All squares pulse together via sinusoidal opacity
            self.lit_squares = [0, 1, 2, 3, 4, 5]
            self.opacity_value = 0.65 + 0.35 * math.sin(time.time() * 2.0)

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

    def __init__(self, session: SessionState, config, user_settings=None, parent=None):
        super().__init__(parent)

        self.session = session
        self.config = config
        self.user_settings = user_settings

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

        # Context progress bar
        self.context_bar = QProgressBar()
        self.context_bar.setRange(0, 100)
        self.context_bar.setValue(0)
        self.context_bar.setFixedHeight(6)
        self.context_bar.setTextVisible(False)
        self.context_bar.setVisible(False)
        self._update_context_bar_color(0)
        text_layout.addWidget(self.context_bar)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Update animation
        self.update_animation()

    def _get_status_text(self) -> str:
        """Get status text, with permission mode badge for non-default modes."""
        text = self.session.active_tool.display_name if self.session.active_tool else "Idle"
        mode = self.session.permission_mode
        if mode and mode not in ("", "normal", "default"):
            text += f"  [{mode}]"
        return text

    def _get_context_text(self) -> str:
        """Get context percentage text."""
        if self.session.context_percent > 0:
            return f"Context: {self.session.context_percent:.1f}%"
        return ""

    def _update_context_bar_color(self, percent: int):
        """Set progress bar color based on usage thresholds."""
        if percent >= 80:
            color = "#EF4444"  # red
        elif percent >= 50:
            color = "#F59E0B"  # amber
        else:
            color = "#22C55E"  # green
        self.context_bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {color};
                border-radius: 3px;
            }}
        """)

    def update_animation(self):
        """Update animation based on current session state."""
        speed = 1.0
        enabled = True
        if self.user_settings:
            speed = self.user_settings.get("animation_speed_multiplier")
            enabled = self.user_settings.get("animations_enabled")

        if self.session.active_tool:
            tool = self.session.active_tool
            color_rgb = self.config.get_color_rgb(tool.color)
            pattern_config = self.config.get_pattern_config(tool.pattern)
            attention_config = self.config.get_attention_config(tool.attention)

            # Duration evolution: slow animation for long-running tools
            elapsed = time.time() - tool.started_at
            level_name, duration_mult = self.config.get_duration_speed_mult(elapsed)
            if not hasattr(self, '_last_duration_level') or self._last_duration_level != level_name:
                self._last_duration_level = level_name
                effective_speed = speed * duration_mult
                self.activity_indicator.set_pattern(
                    tool.pattern, color_rgb, pattern_config,
                    speed_multiplier=effective_speed, animations_enabled=enabled,
                    attention_config=attention_config,
                )
        else:
            # Idle - dormant pattern
            self._last_duration_level = "normal"
            color_rgb = self.config.get_color_rgb('slate')
            pattern_config = self.config.get_pattern_config('dormant')
            idle_attention = self.config.get_attention_config('peripheral')
            self.activity_indicator.set_pattern(
                'dormant', color_rgb, pattern_config,
                speed_multiplier=speed, animations_enabled=enabled,
                attention_config=idle_attention,
            )

    def update_display(self):
        """Update display labels."""
        self.project_label.setText(self.session.display_name)
        self.status_label.setText(self._get_status_text())
        self.context_label.setText(self._get_context_text())
        percent = int(self.session.context_percent)
        self.context_bar.setValue(percent)
        self.context_bar.setVisible(percent > 0)
        self._update_context_bar_color(percent)
        self.update_animation()


class ClaudeNotchOverlay(QWidget):
    """
    Main overlay window.
    Transparent, frameless window showing Claude activity.
    """

    def __init__(self, state_manager: StateManager, user_settings=None, parent=None):
        super().__init__(parent)

        self.state_manager = state_manager
        self.config = state_manager.config
        self.user_settings = user_settings
        self.session_cards = {}  # session_id -> SessionCard
        self._user_dragged = False  # True after user drags overlay
        self._is_fading_out = False  # Guard against show during hide cleanup

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

        # Connect user settings
        if self.user_settings:
            self.user_settings.settings_changed.connect(self._on_setting_changed)

        # Position window
        self._position_window()

        # Fade animation for show/hide
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(200)
        self._fade_animation.setEasingCurve(QEasingCurve.InOutCubic)

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
        """Position window at the configured screen corner."""
        screen = QGuiApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        padding = 20

        position = "top-right"
        if self.user_settings:
            position = self.user_settings.get("screen_position")

        if position == "top-left":
            x = screen_rect.left() + padding
            y = screen_rect.top() + padding
        elif position == "bottom-right":
            x = screen_rect.right() - self.width() - padding
            y = screen_rect.bottom() - self.height() - padding
        elif position == "bottom-left":
            x = screen_rect.left() + padding
            y = screen_rect.bottom() - self.height() - padding
        else:  # top-right (default)
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
                card = SessionCard(session, self.config, user_settings=self.user_settings)
                self.session_cards[session.session_id] = card
                self.layout.addWidget(card)

        # Show/hide window based on activity and auto_hide setting
        auto_hide = True
        if self.user_settings:
            auto_hide = self.user_settings.get("auto_hide")

        should_show = False
        if auto_hide:
            should_show = bool(sessions) and not self.state_manager.is_idle
        else:
            should_show = bool(sessions)

        if should_show:
            if not self.isVisible() and not self._is_fading_out:
                self._animated_show()
        else:
            if self.isVisible() and not self._is_fading_out:
                self._animated_hide()

        # Adjust window size
        self.adjustSize()
        if self._user_dragged:
            self._clamp_to_screen()
        else:
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
        opacity = 220
        if self.user_settings:
            opacity = self.user_settings.get("background_opacity")
        bg_color = QColor(20, 20, 20, opacity)
        painter.setBrush(QBrush(bg_color))
        painter.setPen(Qt.NoPen)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 15, 15)
        painter.drawPath(path)

    def _animated_show(self):
        """Show overlay with fade-in animation."""
        animations_enabled = True
        if self.user_settings:
            animations_enabled = self.user_settings.get("animations_enabled")

        self._is_fading_out = False
        if not animations_enabled:
            self.setWindowOpacity(1.0)
            self.show()
            return

        self._fade_animation.stop()
        self.setWindowOpacity(0.0)
        self.show()
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        try:
            self._fade_animation.finished.disconnect()
        except RuntimeError:
            pass
        self._fade_animation.finished.connect(self._on_show_finished)
        self._fade_animation.start()

    def _on_show_finished(self):
        """Safety net: ensure full opacity after show animation."""
        self.setWindowOpacity(1.0)

    def _animated_hide(self):
        """Hide overlay with fade-out animation."""
        animations_enabled = True
        if self.user_settings:
            animations_enabled = self.user_settings.get("animations_enabled")

        if not animations_enabled:
            self.hide()
            return

        self._is_fading_out = True
        self._fade_animation.stop()
        self._fade_animation.setStartValue(self.windowOpacity())
        self._fade_animation.setEndValue(0.0)
        try:
            self._fade_animation.finished.disconnect()
        except RuntimeError:
            pass
        self._fade_animation.finished.connect(self._on_hide_finished)
        self._fade_animation.start()

    def _on_hide_finished(self):
        """Complete the hide after fade-out."""
        self.hide()
        self._is_fading_out = False
        self.setWindowOpacity(1.0)

    def _clamp_to_screen(self):
        """Clamp overlay position to screen edges after drag + resize."""
        screen = QGuiApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        pos = self.pos()
        x = max(screen_rect.left(), min(pos.x(), screen_rect.right() - self.width()))
        y = max(screen_rect.top(), min(pos.y(), screen_rect.bottom() - self.height()))
        self.move(x, y)

    def reset_position(self):
        """Reset overlay to configured corner (called from tray menu)."""
        self._user_dragged = False
        self._position_window()

    def _on_setting_changed(self, key: str):
        """React to user setting changes."""
        if key == "screen_position":
            self._user_dragged = False
            self._position_window()
        elif key == "background_opacity":
            self.update()  # triggers paintEvent
        elif key == "auto_hide":
            self._update_sessions()
        elif key in ("animation_speed_multiplier", "animations_enabled"):
            for card in self.session_cards.values():
                card.update_animation()

    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            self._user_dragged = True
            event.accept()
