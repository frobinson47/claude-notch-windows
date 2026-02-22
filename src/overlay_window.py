"""
Floating overlay window that displays Claude Code activity.
Transparent, click-through window positioned at top-right of screen.
Enhanced with glow effects, smooth transitions, particles, and accent borders.
"""

import logging
import math
import random
import time
from typing import List, Optional
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar
from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont, QGuiApplication,
    QRadialGradient, QLinearGradient,
)
from state_manager import StateManager, SessionState

logger = logging.getLogger(__name__)


class ActivityIndicator(QWidget):
    """
    3x2 grid animation showing activity pattern.
    Enhanced with glow halos, smooth per-square opacity transitions,
    gradient fills, drop shadows, specular highlights, and particles.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFixedSize(140, 95)

        # Animation state
        self.lit_squares = []
        self.color = QColor(249, 115, 22)  # Default orange
        self.opacity_value = 0.8
        self.pattern_config = None
        self.sequence_index = 0

        # Smooth per-square opacity
        self._square_opacities = [0.0] * 6
        self._target_opacities = [0.0] * 6

        # Particles (for random-mode patterns)
        self._particles = []
        self._particle_mode = False

        # Animation timer (pattern step)
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_step)

        # Smooth interpolation timer (~60fps)
        self._lerp_timer = QTimer()
        self._lerp_timer.timeout.connect(self._lerp_step)
        self._lerp_timer.start(16)

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

        # Enable particles for random-mode patterns
        mode = config.get('mode', 'static')
        self._particle_mode = (mode == 'random')

        if not animations_enabled:
            # Show static first frame — set opacities instantly
            self.animation_timer.stop()
            sequence = config.get('sequence', [[]])
            self.lit_squares = sequence[0] if sequence else []
            for i in range(6):
                val = self.opacity_value if i in self.lit_squares else 0.0
                self._square_opacities[i] = val
                self._target_opacities[i] = val
            self._particles.clear()
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
        """Stop the animation with a smooth fade-out."""
        self.animation_timer.stop()
        self.lit_squares = []
        self._particles.clear()
        # Fade all squares to zero
        for i in range(6):
            self._target_opacities[i] = 0.0
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
            # Emit particles for random modes
            if self._particle_mode:
                self._emit_particles(2)

        elif mode == 'breathe':
            # All squares pulse together via sinusoidal opacity
            self.lit_squares = [0, 1, 2, 3, 4, 5]
            self.opacity_value = 0.65 + 0.35 * math.sin(time.time() * 2.0)

        elif mode == 'static':
            # Static pattern
            sequence = self.pattern_config.get('sequence', [[]])
            self.lit_squares = sequence[0] if sequence else []

        # Update target opacities for smooth transitions
        for i in range(6):
            if i in self.lit_squares:
                self._target_opacities[i] = self.opacity_value
            else:
                self._target_opacities[i] = 0.0

        self.update()

    def _lerp_step(self):
        """Smoothly interpolate square opacities toward targets (~60fps)."""
        changed = False
        lerp_speed = 0.18

        for i in range(6):
            diff = self._target_opacities[i] - self._square_opacities[i]
            if abs(diff) > 0.005:
                self._square_opacities[i] += diff * lerp_speed
                changed = True
            elif self._square_opacities[i] != self._target_opacities[i]:
                self._square_opacities[i] = self._target_opacities[i]
                changed = True

        # Update particles
        if self._particles:
            self._update_particles()
            changed = True

        if changed:
            self.update()

    def _emit_particles(self, count=2):
        """Emit small particles from lit squares."""
        if not self.lit_squares:
            return
        sources = random.sample(
            self.lit_squares, min(2, len(self.lit_squares))
        )
        square_size = 30
        gap = 5
        margin = 10
        for idx in sources:
            row = idx // 3
            col = idx % 3
            cx = col * (square_size + gap) + margin + square_size / 2
            cy = row * (square_size + gap) + margin + square_size / 2
            for _ in range(count):
                self._particles.append({
                    'x': cx + random.uniform(-4, 4),
                    'y': cy + random.uniform(-4, 4),
                    'vx': random.uniform(-1.2, 1.2),
                    'vy': random.uniform(-1.8, -0.3),
                    'life': 1.0,
                    'decay': random.uniform(0.025, 0.06),
                    'size': random.uniform(1.0, 2.5),
                })

    def _update_particles(self):
        """Update particle positions and lifetimes."""
        alive = []
        for p in self._particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] -= 0.02  # slight upward drift
            p['life'] -= p['decay']
            if p['life'] > 0:
                alive.append(p)
        self._particles = alive[:40]  # cap count

    def set_opacity(self, value: float):
        """Set opacity value (0.0 - 1.0)."""
        self.opacity_value = max(0.0, min(1.0, value))
        self.update()

    def paintEvent(self, event):
        """Paint the 3x2 grid with glow, gradients, shadows, and particles."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        square_size = 30
        gap = 5
        margin = 10

        for i in range(6):
            row = i // 3
            col = i % 3

            x = col * (square_size + gap) + margin
            y = row * (square_size + gap) + margin
            center_x = x + square_size / 2
            center_y = y + square_size / 2

            sq_opacity = self._square_opacities[i]

            if sq_opacity > 0.03:
                # --- Glow halo (radial gradient behind square) ---
                glow_radius = square_size * 0.85
                glow = QRadialGradient(center_x, center_y, glow_radius)
                glow_inner = QColor(self.color)
                glow_inner.setAlphaF(sq_opacity * 0.25)
                glow_outer = QColor(self.color)
                glow_outer.setAlphaF(0.0)
                glow.setColorAt(0.0, glow_inner)
                glow.setColorAt(0.6, glow_inner)
                glow.setColorAt(1.0, glow_outer)
                painter.setBrush(QBrush(glow))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(
                    QPointF(center_x, center_y), glow_radius, glow_radius
                )

                # --- Drop shadow ---
                shadow = QColor(0, 0, 0, int(60 * sq_opacity))
                painter.setBrush(QBrush(shadow))
                painter.drawRoundedRect(
                    int(x + 2), int(y + 2), square_size, square_size, 5, 5
                )

                # --- Lit square (linear gradient fill) ---
                sq_grad = QLinearGradient(x, y, x, y + square_size)
                top_color = QColor(self.color)
                top_color.setAlphaF(sq_opacity)
                bot_color = QColor(self.color).darker(140)
                bot_color.setAlphaF(sq_opacity * 0.75)
                sq_grad.setColorAt(0.0, top_color)
                sq_grad.setColorAt(1.0, bot_color)
                painter.setBrush(QBrush(sq_grad))
                painter.drawRoundedRect(x, y, square_size, square_size, 5, 5)

                # --- Specular highlight (top half gloss) ---
                hl_grad = QLinearGradient(x, y, x, y + square_size * 0.5)
                hl_top = QColor(255, 255, 255, int(40 * sq_opacity))
                hl_bot = QColor(255, 255, 255, 0)
                hl_grad.setColorAt(0.0, hl_top)
                hl_grad.setColorAt(1.0, hl_bot)
                painter.setBrush(QBrush(hl_grad))
                painter.drawRoundedRect(
                    x + 2, y + 1,
                    square_size - 4, int(square_size * 0.45),
                    3, 3,
                )
            else:
                # --- Dim square ---
                dim = QColor(80, 80, 85, int(35 * self.opacity_value))
                painter.setBrush(QBrush(dim))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(x, y, square_size, square_size, 5, 5)

        # --- Particles ---
        for p in self._particles:
            p_color = QColor(self.color)
            p_color.setAlphaF(max(0.0, min(1.0, p['life'] * 0.5)))
            painter.setBrush(QBrush(p_color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(p['x'], p['y']), p['size'], p['size'])


class TimelineStrip(QWidget):
    """
    Thin color bar showing recent tool history as colored segments.
    Coalesces consecutive same-category entries. Newest on the left.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)
        self._segments = []  # list of (QColor, weight)

    def set_tools(self, recent_tools: list, config):
        """Build coalesced segments from recent_tools list.

        Args:
            recent_tools: List of ActiveTool (newest first).
            config: NotchConfig for color lookup.
        """
        if not recent_tools:
            self._segments = []
            self.setVisible(False)
            return

        segments = []
        prev_category = None
        for tool in recent_tools:
            if tool.category == prev_category and segments:
                # Coalesce: increment weight of last segment
                color, weight = segments[-1]
                segments[-1] = (color, weight + 1)
            else:
                rgb = config.get_color_rgb(tool.color)
                segments.append((QColor(*rgb), 1))
                prev_category = tool.category

        self._segments = segments
        self.setVisible(True)
        self.update()

    def paintEvent(self, event):
        if not self._segments:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        total_weight = sum(w for _, w in self._segments)
        gap = 1
        total_gaps = (len(self._segments) - 1) * gap
        available = self.width() - total_gaps

        x = 0.0
        for i, (color, weight) in enumerate(self._segments):
            seg_width = max(1.0, (weight / total_weight) * available)
            c = QColor(color)
            c.setAlphaF(0.7)
            painter.setBrush(QBrush(c))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(x, 0, seg_width, self.height()), 2, 2)
            x += seg_width + gap


class ContextRing(QWidget):
    """Circular arc indicator for context window usage."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._percent = 0
        self._color = QColor(34, 197, 94)

    def set_percent(self, percent: int):
        self._percent = max(0, min(100, percent))
        if percent >= 80:
            self._color = QColor(239, 68, 68)   # red
        elif percent >= 50:
            self._color = QColor(245, 158, 11)  # amber
        else:
            self._color = QColor(34, 197, 94)   # green
        self.update()

    def paintEvent(self, event):
        if self._percent <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        size = min(self.width(), self.height())
        margin = 4
        rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)

        # Background ring
        bg_pen = QPen(QColor(255, 255, 255, 25), 2.5)
        bg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(rect)

        # Foreground arc
        fg_pen = QPen(self._color, 2.5)
        fg_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(fg_pen)
        span_angle = int(-self._percent * 360 / 100 * 16)
        painter.drawArc(rect, 90 * 16, span_angle)

        # Percentage text
        painter.setPen(QColor(255, 255, 255, 160))
        font = QFont()
        font.setPixelSize(9)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{self._percent}")


class SessionCard(QWidget):
    """
    Card displaying a single session's activity.
    Shows project name, tool status, activity indicator, and context ring.
    """

    def __init__(self, session: SessionState, config, user_settings=None, parent=None):
        super().__init__(parent)

        self.session = session
        self.config = config
        self.user_settings = user_settings
        self._flash_opacity = 0.0
        self._flash_animation = None

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI layout."""
        outer = QVBoxLayout(self)
        outer.setContentsMargins(15, 10, 15, 10)
        outer.setSpacing(6)

        # Top row: activity indicator + text + context ring
        top_row = QHBoxLayout()
        top_row.setSpacing(15)

        # Activity indicator
        self.activity_indicator = ActivityIndicator()
        top_row.addWidget(self.activity_indicator)

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

        top_row.addLayout(text_layout)
        top_row.addStretch()

        # Context ring (far right)
        self.context_ring = ContextRing()
        self.context_ring.setVisible(False)
        top_row.addWidget(self.context_ring)

        outer.addLayout(top_row)

        # Bottom row: timeline strip
        self.timeline_strip = TimelineStrip()
        self.timeline_strip.setVisible(False)
        outer.addWidget(self.timeline_strip)

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

    def _get_session_project_color(self) -> Optional[tuple]:
        """Look up per-project accent color for this card's session."""
        if not self.user_settings or not self.session.project_name:
            return None
        project_colors = self.user_settings.get("project_colors")
        color_name = project_colors.get(self.session.project_name)
        if not color_name:
            return None
        if color_name not in self.config.colors:
            return None
        return self.config.get_color_rgb(color_name)

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

            # Detect tool change or duration level change — only then call set_pattern
            # to avoid restarting animations every tick
            tool_key = (tool.tool_name, tool.started_at)
            last_key = getattr(self, '_last_tool_key', None)
            last_level = getattr(self, '_last_duration_level', None)
            if tool_key != last_key or level_name != last_level:
                self._last_tool_key = tool_key
                self._last_duration_level = level_name
                effective_speed = speed * duration_mult
                self.activity_indicator.set_pattern(
                    tool.pattern, color_rgb, pattern_config,
                    speed_multiplier=effective_speed, animations_enabled=enabled,
                    attention_config=attention_config,
                )
        else:
            # Idle - dormant pattern (use project color if configured, else slate)
            self._last_tool_key = None
            self._last_duration_level = "normal"
            project_rgb = self._get_session_project_color()
            color_rgb = project_rgb if project_rgb else self.config.get_color_rgb('slate')
            pattern_config = self.config.get_pattern_config('dormant')
            idle_attention = self.config.get_attention_config('peripheral')
            self.activity_indicator.set_pattern(
                'dormant', color_rgb, pattern_config,
                speed_multiplier=speed, animations_enabled=enabled,
                attention_config=idle_attention,
            )

    def flash_error(self):
        """Trigger a red error flash that fades out over 1.5s."""
        self._flash_opacity = 0.45
        if self._flash_animation is None:
            self._flash_animation = QPropertyAnimation(self, b"flash_opacity_prop")
        self._flash_animation.stop()
        self._flash_animation.setDuration(1500)
        self._flash_animation.setStartValue(0.45)
        self._flash_animation.setEndValue(0.0)
        self._flash_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._flash_animation.start()

    def _get_flash_opacity(self):
        return self._flash_opacity

    def _set_flash_opacity(self, value):
        self._flash_opacity = value
        self.update()

    flash_opacity_prop = Property(float, _get_flash_opacity, _set_flash_opacity)

    def paintEvent(self, event):
        """Paint error flash overlay if active."""
        super().paintEvent(event)
        if self._flash_opacity > 0.01:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            red = QColor(239, 68, 68)
            red.setAlphaF(self._flash_opacity)
            painter.setBrush(QBrush(red))
            painter.setPen(Qt.NoPen)
            path = QPainterPath()
            path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 8, 8)
            painter.drawPath(path)

    def update_display(self):
        """Update display labels."""
        self.project_label.setText(self.session.display_name)
        self.status_label.setText(self._get_status_text())
        self.context_label.setText(self._get_context_text())
        percent = int(self.session.context_percent)
        self.context_ring.set_percent(percent)
        self.context_ring.setVisible(percent > 0)
        self.update_animation()

        # Update timeline strip
        self.timeline_strip.set_tools(self.session.recent_tools, self.config)


class MiniSessionCard(QWidget):
    """
    Compact single-line card displaying a session's activity.
    Shows a color dot, project name, and tool status.
    """

    def __init__(self, session: SessionState, config, user_settings=None, parent=None):
        super().__init__(parent)

        self.session = session
        self.config = config
        self.user_settings = user_settings

        self.setFixedHeight(26)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # Color dot
        self._dot = _ColorDot()
        layout.addWidget(self._dot)

        # Project name
        self._project_label = QLabel(self.session.display_name)
        self._project_label.setStyleSheet(
            "color: white; font-size: 12px; font-weight: bold;"
        )
        layout.addWidget(self._project_label)

        # Status
        self._status_label = QLabel(self._get_status_text())
        self._status_label.setStyleSheet(
            "color: rgba(255,255,255,0.55); font-size: 11px;"
        )
        layout.addWidget(self._status_label)
        layout.addStretch()

        self._update_dot_color()

    def _get_status_text(self) -> str:
        return self.session.active_tool.display_name if self.session.active_tool else "Idle"

    def _get_dot_color(self) -> QColor:
        """Determine dot color: project color > tool color > slate."""
        if self.user_settings and self.session.project_name:
            project_colors = self.user_settings.get("project_colors")
            color_name = project_colors.get(self.session.project_name)
            if color_name and color_name in self.config.colors:
                return QColor(*self.config.get_color_rgb(color_name))
        if self.session.active_tool:
            return QColor(*self.config.get_color_rgb(self.session.active_tool.color))
        return QColor(*self.config.get_color_rgb('slate'))

    def _update_dot_color(self):
        self._dot.color = self._get_dot_color()
        self._dot.update()

    def update_display(self):
        self._project_label.setText(self.session.display_name)
        self._status_label.setText(self._get_status_text())
        self._update_dot_color()

    def update_animation(self):
        """No-op — mini mode has no animations."""

    def flash_error(self):
        """No-op — mini mode has no error flash."""


class _ColorDot(QWidget):
    """8x8 painted circle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(8, 8)
        self.color = QColor(120, 120, 130)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self.color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 8, 8)


class ClaudeNotchOverlay(QWidget):
    """
    Main overlay window.
    Transparent, frameless window showing Claude activity.
    Enhanced with colored accent border reflecting the active tool.
    """

    def __init__(self, state_manager: StateManager, user_settings=None,
                 notification_manager=None, parent=None):
        super().__init__(parent)

        self.state_manager = state_manager
        self.config = state_manager.config
        self.user_settings = user_settings
        self.notification_manager = notification_manager
        self.session_cards = {}  # session_id -> SessionCard or MiniSessionCard
        self._user_dragged = False  # True after user drags overlay
        self._is_fading_out = False  # Guard against show during hide cleanup
        self._accent_color = None   # Current border accent color
        self._mini_mode = user_settings.get("mini_mode") if user_settings else False

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

        # Connect notification manager for error flashes
        if self.notification_manager:
            self.notification_manager.error_flash.connect(self._on_error_flash)

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

        # Set minimum size based on mode
        if self._mini_mode:
            self.setMinimumSize(250, 30)
        else:
            self.setMinimumSize(400, 100)

    def _get_target_screen(self):
        """Get the target screen from settings, falling back to primary."""
        target_name = ""
        if self.user_settings:
            target_name = self.user_settings.get("target_monitor")
        if target_name:
            for screen in QGuiApplication.screens():
                if screen.name() == target_name:
                    return screen
        return QGuiApplication.primaryScreen()

    def _position_window(self):
        """Position window at the configured screen corner."""
        screen = self._get_target_screen()
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

    def _on_error_flash(self, session_id: str):
        """Trigger red flash on the matching session card."""
        card = self.session_cards.get(session_id)
        if card:
            card.flash_error()

    def _get_project_color(self, session) -> Optional[tuple]:
        """Look up per-project accent color. Returns RGB tuple or None."""
        if not self.user_settings or not session.project_name:
            return None
        project_colors = self.user_settings.get("project_colors")
        color_name = project_colors.get(session.project_name)
        if not color_name:
            return None
        # Validate color exists in config
        if color_name not in self.config.colors:
            return None
        return self.config.get_color_rgb(color_name)

    def _update_accent_color(self):
        """Determine accent color: project color > tool color > None."""
        for card in self.session_cards.values():
            # Check project color first
            project_rgb = self._get_project_color(card.session)
            if project_rgb:
                new_color = QColor(*project_rgb)
                if self._accent_color != new_color:
                    self._accent_color = new_color
                    self.update()
                return
            if card.session.active_tool:
                color_rgb = self.config.get_color_rgb(card.session.active_tool.color)
                new_color = QColor(*color_rgb)
                if self._accent_color != new_color:
                    self._accent_color = new_color
                    self.update()  # repaint border accent
                return
        if self._accent_color is not None:
            self._accent_color = None
            self.update()

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
                # Create new card (mini or full)
                if self._mini_mode:
                    card = MiniSessionCard(session, self.config, user_settings=self.user_settings)
                else:
                    card = SessionCard(session, self.config, user_settings=self.user_settings)
                self.session_cards[session.session_id] = card
                self.layout.addWidget(card)

        # Update accent color
        self._update_accent_color()

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
        self._update_accent_color()

    def paintEvent(self, event):
        """Paint semi-transparent background with colored accent border."""
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

        # --- Border accent (colored line at top, reflecting active tool) ---
        if self._accent_color:
            painter.setClipPath(path)

            # Gradient accent line that fades at the edges
            accent_grad = QLinearGradient(0, 0, self.width(), 0)
            ac_transparent = QColor(self._accent_color)
            ac_transparent.setAlphaF(0.0)
            ac_solid = QColor(self._accent_color)
            ac_solid.setAlphaF(0.7)
            accent_grad.setColorAt(0.0, ac_transparent)
            accent_grad.setColorAt(0.15, ac_solid)
            accent_grad.setColorAt(0.85, ac_solid)
            accent_grad.setColorAt(1.0, ac_transparent)

            painter.setPen(QPen(QBrush(accent_grad), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawLine(QPointF(0, 1), QPointF(self.width(), 1))

            # Soft glow bleed below the accent line
            glow_grad = QLinearGradient(0, 0, 0, 10)
            g_top = QColor(self._accent_color)
            g_top.setAlphaF(0.12)
            g_bot = QColor(self._accent_color)
            g_bot.setAlphaF(0.0)
            glow_grad.setColorAt(0, g_top)
            glow_grad.setColorAt(1, g_bot)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(glow_grad))
            painter.drawRect(QRectF(0, 0, self.width(), 10))

            painter.setClipping(False)

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
        screen = self._get_target_screen()
        screen_rect = screen.availableGeometry()
        pos = self.pos()
        x = max(screen_rect.left(), min(pos.x(), screen_rect.right() - self.width()))
        y = max(screen_rect.top(), min(pos.y(), screen_rect.bottom() - self.height()))
        self.move(x, y)

    def reset_position(self):
        """Reset overlay to configured corner (called from tray menu)."""
        self._user_dragged = False
        self._position_window()

    def _rebuild_cards(self):
        """Clear all session cards and recreate them (used when card type changes)."""
        for card in self.session_cards.values():
            self.layout.removeWidget(card)
            card.deleteLater()
        self.session_cards.clear()
        # Update minimum size for new mode
        if self._mini_mode:
            self.setMinimumSize(250, 30)
        else:
            self.setMinimumSize(400, 100)
        self._update_sessions()

    def _on_setting_changed(self, key: str):
        """React to user setting changes."""
        if key == "mini_mode":
            self._mini_mode = self.user_settings.get("mini_mode")
            self._rebuild_cards()
        elif key in ("screen_position", "target_monitor"):
            self._user_dragged = False
            self._position_window()
        elif key == "background_opacity":
            self.update()  # triggers paintEvent
        elif key == "auto_hide":
            self._update_sessions()
        elif key in ("animation_speed_multiplier", "animations_enabled"):
            for card in self.session_cards.values():
                card.update_animation()
        elif key == "project_colors":
            self._update_accent_color()
            for card in self.session_cards.values():
                card.update_animation()

    def toggle_visibility(self):
        """Toggle overlay show/hide (used by global hotkey)."""
        if self.isVisible() and not self._is_fading_out:
            self._animated_hide()
        elif not self.isVisible():
            self._is_fading_out = False
            self._animated_show()

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
