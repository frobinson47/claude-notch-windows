"""
State management for Claude Code sessions and tool tracking.
Manages session state, active tools, token usage, and UI updates.
"""

import json
import logging
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List, Set
from PySide6.QtCore import QObject, QTimer, Signal

logger = logging.getLogger(__name__)


@dataclass
class ActiveTool:
    """Represents an active tool being used by Claude."""
    tool_name: str
    started_at: float = field(default_factory=time.time)
    description: str = ""
    category: str = "think"
    display_name: str = "Working"
    color: str = "orange"
    pattern: str = "cogitate"
    attention: str = "ambient"


@dataclass
class TokenStats:
    """Token usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def total_cost_tokens(self) -> int:
        """Total tokens for cost calculation (includes cache creation)."""
        return self.total_tokens + self.cache_creation_tokens


@dataclass
class SessionState:
    """Represents a Claude Code session."""
    session_id: str
    project_path: str
    project_name: str
    start_time: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    active_tool: Optional[ActiveTool] = None
    recent_tools: List[ActiveTool] = field(default_factory=list)
    is_active: bool = True
    permission_mode: str = "normal"
    token_stats: TokenStats = field(default_factory=TokenStats)
    context_percent: float = 0.0
    context_tokens: int = 0
    terminal_hwnd: Optional[int] = None

    @property
    def display_name(self) -> str:
        """Get display name for session."""
        return self.project_name or Path(self.project_path).name or "Unknown"

    @property
    def status_text(self) -> str:
        """Get status text for session."""
        if self.active_tool:
            return f"{self.active_tool.display_name} - {self.display_name}"
        return f"Idle - {self.display_name}"

    @property
    def is_stale(self) -> bool:
        """Check if session is stale (no activity for >60s). Use is_stale_at for dynamic timeout."""
        return time.time() - self.last_activity > 60

    def is_stale_at(self, timeout: int = 60) -> bool:
        """Check if session is stale with a configurable timeout."""
        return time.time() - self.last_activity > timeout


class NotchConfig:
    """Loads and manages notch-config.json configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        """Load configuration from JSON file."""
        if config_path is None:
            # Support PyInstaller bundled path
            base = getattr(sys, '_MEIPASS', Path(__file__).parent.parent)
            config_path = Path(base) / "config" / "notch-config.json"

        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.categories = self.config.get('categories', {})
        self.tools = self.config.get('tools', {})
        self.states = self.config.get('states', {})
        self.patterns = self.config.get('patterns', {})
        self.colors = self.config.get('colors', {})
        self.defaults = self.config.get('defaults', {})
        self.attention_levels = self.config.get('attention_levels', {})

    def get_tool_info(self, tool_name: str) -> Dict:
        """Get tool configuration with category info merged."""
        tool_name_lower = tool_name.lower()

        # Get tool config (or use default)
        tool_config = self.tools.get(tool_name_lower, self.defaults.get('unknownTool', {}))

        # Get category name
        category_name = tool_config.get('category', 'think')

        # Get category config
        category_config = self.categories.get(category_name, {})

        # Merge tool and category config
        return {
            'tool_name': tool_name,
            'display_name': tool_config.get('displayName', tool_name.title()),
            'category': category_name,
            'color': category_config.get('color', 'orange'),
            'pattern': category_config.get('pattern', 'cogitate'),
            'intensity': category_config.get('intensity', 2),
            'attention': category_config.get('attention', 'ambient'),
            'description': category_config.get('description', ''),
        }

    def get_color_rgb(self, color_name: str) -> tuple:
        """Get RGB tuple for a color name."""
        color_config = self.colors.get(color_name, self.colors.get('orange', {}))
        return tuple(color_config.get('rgb', [249, 115, 22]))

    def get_pattern_config(self, pattern_name: str) -> Dict:
        """Get pattern configuration."""
        return self.patterns.get(pattern_name, self.patterns.get('cogitate', {}))

    def get_attention_config(self, attention_level: str) -> Dict:
        """Get attention level config (opacity range, pulse flag)."""
        return self.attention_levels.get(attention_level, self.attention_levels.get('ambient', {}))

    def get_duration_speed_mult(self, elapsed_seconds: float) -> tuple:
        """Return (level_name, speed_multiplier) for duration evolution."""
        evolution = self.config.get('duration_evolution', {})
        for level_name in ['normal', 'extended', 'long', 'stuck']:
            level = evolution.get(level_name, {})
            until = level.get('until')
            if until is None or elapsed_seconds < until:
                return (level_name, level.get('speedMult', 1.0))
        return ('stuck', 0.3)


class StateManager(QObject):
    """
    Central state manager for Claude Code activity.
    Emits Qt signals for UI updates.
    """

    # Qt signals for UI updates
    session_updated = Signal(str)  # session_id
    session_ended = Signal(str)  # session_id
    tool_started = Signal(str, str)  # session_id, tool_name
    tool_ended = Signal(str, str)  # session_id, tool_name
    activity_changed = Signal()  # General activity change
    notification_received = Signal(str, str)  # session_id, message
    error_detected = Signal(str, str)  # session_id, tool_name
    attention_needed = Signal(str)  # session_id

    def __init__(self, config: Optional[NotchConfig] = None, user_settings=None):
        """Initialize state manager."""
        super().__init__()

        self.config = config or NotchConfig()
        self.user_settings = user_settings
        self.sessions: Dict[str, SessionState] = {}
        self.pinned_paths: Set[str] = set()
        self.active_session_id: Optional[str] = None
        self.last_activity_time = time.time()

        # Grace period timer — shows "Thinking" between tool calls instead of "Idle"
        self._grace_timer = QTimer(self)
        self._grace_timer.setSingleShot(True)
        self._grace_timer.timeout.connect(self._on_grace_expired)
        self._grace_session_id: Optional[str] = None

        # Load grace period (seconds) and fun verbs from config
        self._grace_period_ms = int(self.config.defaults.get('gracePeriod', 3) * 1000)
        thinking_state = self.config.states.get('thinking', {})
        self._fun_verbs = thinking_state.get('funVerbs', ['Thinking'])

        from session_stats import SessionStats
        self.session_stats = SessionStats()

    def handle_event(self, event_type: str, data: dict):
        """
        Handle hook event from Claude Code.

        Args:
            event_type: Type of event ('hook', 'pin', 'unpin')
            data: Event payload
        """
        if event_type == 'hook':
            self._handle_hook_event(data)
        elif event_type == 'pin':
            self._handle_pin_event(data)
        elif event_type == 'unpin':
            self._handle_unpin_event(data)

    def _handle_hook_event(self, data: dict):
        """Handle a Claude Code hook event."""
        event_name = data.get('eventType', '')
        session_id = data.get('sessionId', 'default')
        cwd = data.get('cwd', '')

        logger.debug(f"Hook event: {event_name} | tool: {data.get('tool', 'N/A')} | session: {session_id}")

        # Update last activity time
        self.last_activity_time = time.time()

        # Get or create session
        session = self._get_or_create_session(session_id, cwd)
        session.last_activity = time.time()

        # Save permission mode if present
        perm_mode = data.get('permissionMode')
        if perm_mode:
            session.permission_mode = perm_mode

        # Handle different event types
        if event_name == 'PreToolUse':
            self._handle_pre_tool_use(session, data)
        elif event_name == 'PostToolUse':
            self._handle_post_tool_use(session, data)
        elif event_name in ['Stop', 'SubagentStop']:
            self._handle_stop(session)
        elif event_name == 'SessionStart':
            self._handle_session_start(session, data)
        elif event_name == 'SessionEnd':
            self._handle_session_end(session)
        elif event_name == 'Notification':
            self._handle_notification(session, data)
        elif event_name == 'UserPromptSubmit':
            self._handle_user_prompt(session, data)

        # Update token usage from transcript if available
        self._update_token_usage(session, data)

        # Emit update signal
        self.session_updated.emit(session_id)
        self.activity_changed.emit()

    def _handle_pre_tool_use(self, session: SessionState, data: dict):
        """Handle PreToolUse event."""
        # Cancel any running grace timer — real tool is starting
        self._grace_timer.stop()

        tool_name = data.get('tool', 'unknown')
        tool_input = data.get('toolInput', {})

        # Detect attention-needed events
        if tool_name == 'AskUserQuestion':
            self.attention_needed.emit(session.session_id)

        # Get tool info from config
        tool_info = self.config.get_tool_info(tool_name)

        # Create active tool
        active_tool = ActiveTool(
            tool_name=tool_name,
            display_name=tool_info['display_name'],
            category=tool_info['category'],
            color=tool_info['color'],
            pattern=tool_info['pattern'],
            description=tool_info['description'],
            attention=tool_info['attention'],
        )

        session.active_tool = active_tool
        session.is_active = True

        # Add to recent tools
        session.recent_tools.insert(0, active_tool)
        session.recent_tools = session.recent_tools[:10]  # Keep last 10

        self.tool_started.emit(session.session_id, tool_name)

    def _handle_post_tool_use(self, session: SessionState, data: dict):
        """Handle PostToolUse event."""
        # Tool finished — transition to "Thinking" state for the grace period
        tool_name = data.get('tool', '')
        if session.active_tool:
            self.tool_ended.emit(session.session_id, session.active_tool.tool_name)

        # Detect errors in Bash tool results
        if tool_name == 'Bash':
            self._check_bash_error(session, data)

        # Record tool usage stats (exclude synthetic _thinking tool)
        if session.active_tool and session.active_tool.tool_name != '_thinking':
            elapsed = time.time() - session.active_tool.started_at
            self.session_stats.record_tool_use(
                session.active_tool.tool_name,
                session.active_tool.category,
                elapsed
            )

        self._start_grace_period(session)

    def _handle_stop(self, session: SessionState):
        """Handle Stop event (Claude finished responding)."""
        if session.active_tool:
            self.tool_ended.emit(session.session_id, session.active_tool.tool_name)
        self._start_grace_period(session)
        session.is_active = False

    def _handle_session_start(self, session: SessionState, data: dict):
        """Handle SessionStart event."""
        session.start_time = time.time()
        session.is_active = True

        # Capture terminal HWND for click-to-focus
        pid = data.get('pid')
        if pid and self.user_settings and self.user_settings.get('click_to_focus'):
            try:
                from window_focus import find_terminal_hwnd
                session.terminal_hwnd = find_terminal_hwnd(pid)
            except Exception:
                pass

    def _handle_session_end(self, session: SessionState):
        """Handle SessionEnd event."""
        session.is_active = False
        self.session_ended.emit(session.session_id)
        self.session_stats.increment_session_count()

        # Remove session after a delay (keep it visible for a bit)
        # In production, you might want to use a timer for this

    def _handle_user_prompt(self, session: SessionState, data: dict):
        """Handle UserPromptSubmit event."""
        session.is_active = True

    def _handle_notification(self, session: SessionState, data: dict):
        """Handle Notification event — emit signal for tray balloon."""
        tool_input = data.get('toolInput', {})
        if isinstance(tool_input, dict):
            message = tool_input.get('message', '') or tool_input.get('title', '')
        else:
            message = str(tool_input) if tool_input else ''
        if message:
            self.notification_received.emit(session.session_id, message)

    # Heuristic error patterns — only checked in stderr, not stdout,
    # to reduce false positives from commands that mention "error" in normal output.
    _STDERR_ERROR_PATTERNS = (
        'command not found',
        'No such file or directory',
        'Permission denied',
        'Traceback (most recent call last)',
    )

    def _check_bash_error(self, session: SessionState, data: dict):
        """Check Bash tool result for error indicators.

        Priority: structured exit code first, then stderr heuristics as fallback.
        Stdout is NOT scanned to avoid false positives from tools that print
        the word "error" in normal output (e.g. grep, test runners).
        """
        try:
            tool_result = data.get('toolResult')
            if not tool_result:
                return

            # Structured dict with exitCode — authoritative signal
            if isinstance(tool_result, dict):
                exit_code = tool_result.get('exitCode')
                if exit_code is not None and exit_code != 0:
                    self.error_detected.emit(session.session_id, 'Bash')
                    return
                # If exit code is 0 or absent, check stderr only as fallback
                stderr = tool_result.get('stderr', '')
                if stderr:
                    for pattern in self._STDERR_ERROR_PATTERNS:
                        if pattern in stderr:
                            self.error_detected.emit(session.session_id, 'Bash')
                            return
            # String result — no structured exit code available; skip heuristics
            # to avoid false positives on unstructured output.
        except Exception as e:
            logger.debug(f"Error checking bash result: {e}")

    def _start_grace_period(self, session: SessionState):
        """Transition to 'Thinking' state for the grace period."""
        # Pick a random fun verb from config
        verb = random.choice(self._fun_verbs)

        # Get thinking category info for color/pattern
        thinking_state = self.config.states.get('thinking', {})
        category_name = thinking_state.get('category', 'think')
        category = self.config.categories.get(category_name, {})

        session.active_tool = ActiveTool(
            tool_name='_thinking',
            display_name=verb,
            category=category_name,
            color=category.get('color', 'orange'),
            pattern=category.get('pattern', 'cogitate'),
            attention=category.get('attention', 'ambient'),
        )

        # Start (or restart) the grace timer
        self._grace_session_id = session.session_id
        self._grace_timer.start(self._grace_period_ms)

    def _on_grace_expired(self):
        """Grace period elapsed — clear the synthetic thinking state."""
        if self._grace_session_id and self._grace_session_id in self.sessions:
            session = self.sessions[self._grace_session_id]
            # Only clear if still showing the synthetic thinking tool
            if session.active_tool and session.active_tool.tool_name == '_thinking':
                session.active_tool = None
                self.session_updated.emit(session.session_id)
                self.activity_changed.emit()
        self._grace_session_id = None

    def _handle_pin_event(self, data: dict):
        """Handle session pin event."""
        session_id = data.get('sessionId', '')
        cwd = data.get('cwd', '')

        if cwd:
            self.pinned_paths.add(cwd)
            logger.info(f"Pinned session: {cwd}")
            self.activity_changed.emit()

    def _handle_unpin_event(self, data: dict):
        """Handle session unpin event."""
        self.pinned_paths.clear()
        logger.info("Unpinned all sessions")
        self.activity_changed.emit()

    def _get_or_create_session(self, session_id: str, cwd: str) -> SessionState:
        """Get existing session or create new one."""
        if session_id in self.sessions:
            return self.sessions[session_id]

        # Create new session
        project_path = cwd or "Unknown"
        project_name = Path(project_path).name if project_path != "Unknown" else "Unknown"

        session = SessionState(
            session_id=session_id,
            project_path=project_path,
            project_name=project_name
        )

        self.sessions[session_id] = session
        self.active_session_id = session_id

        return session

    def _update_token_usage(self, session: SessionState, data: dict):
        """Update token usage from transcript data."""
        transcript = data.get('transcript', '')

        if not transcript:
            return

        # Parse transcript to extract token usage
        # The transcript is a JSON string containing conversation history
        try:
            transcript_data = json.loads(transcript) if isinstance(transcript, str) else transcript

            # Calculate total tokens from transcript
            total_input = 0
            total_output = 0
            cache_creation = 0
            cache_read = 0

            for msg in transcript_data.get('messages', []):
                usage = msg.get('usage', {})
                total_input += usage.get('input_tokens', 0)
                total_output += usage.get('output_tokens', 0)
                cache_creation += usage.get('cache_creation_input_tokens', 0)
                cache_read += usage.get('cache_read_input_tokens', 0)

            session.token_stats.input_tokens = total_input
            session.token_stats.output_tokens = total_output
            session.token_stats.cache_creation_tokens = cache_creation
            session.token_stats.cache_read_tokens = cache_read

            # Calculate context percentage (rough estimate)
            # Assume 200k context window
            context_window = 200000
            total_context_tokens = total_input + total_output
            session.context_tokens = total_context_tokens
            session.context_percent = min((total_context_tokens / context_window) * 100, 100)

        except Exception as e:
            logger.debug(f"Error parsing transcript for token usage: {e}")

    def get_status_dict(self) -> dict:
        """Return a serializable dict of current state for the /status endpoint."""
        # Snapshot to avoid RuntimeError if dict mutates during iteration
        sessions_snapshot = dict(self.sessions)
        sessions_list = []
        for s in sessions_snapshot.values():
            session_dict = {
                "session_id": s.session_id,
                "project_name": s.project_name,
                "project_path": s.project_path,
                "is_active": s.is_active,
                "context_percent": round(s.context_percent, 1),
                "permission_mode": s.permission_mode,
                "active_tool": None,
            }
            if s.active_tool:
                session_dict["active_tool"] = {
                    "tool_name": s.active_tool.tool_name,
                    "display_name": s.active_tool.display_name,
                    "category": s.active_tool.category,
                    "attention": s.active_tool.attention,
                    "elapsed_seconds": round(time.time() - s.active_tool.started_at, 1),
                }
            sessions_list.append(session_dict)
        return {
            "status": "running",
            "is_idle": self.is_idle,
            "session_count": len(sessions_list),
            "sessions": sessions_list,
        }

    def get_current_session(self) -> Optional[SessionState]:
        """Get the currently active session."""
        if self.active_session_id and self.active_session_id in self.sessions:
            return self.sessions[self.active_session_id]

        # Return any active session
        for session in self.sessions.values():
            if session.is_active or session.active_tool:
                return session

        return None

    def get_display_sessions(self) -> List[SessionState]:
        """Get sessions to display (active or pinned)."""
        activity_timeout = self._get_activity_timeout()
        display = []

        for session in self.sessions.values():
            # Show if active, has active tool, or is pinned
            if session.is_active or session.active_tool or session.project_path in self.pinned_paths:
                if not session.is_stale_at(activity_timeout):
                    display.append(session)

        return sorted(display, key=lambda s: s.last_activity, reverse=True)

    def cleanup_stale_sessions(self):
        """Remove stale sessions."""
        activity_timeout = self._get_activity_timeout()
        to_remove = []

        for session_id, session in self.sessions.items():
            if session.is_stale_at(activity_timeout) and not session.is_active and session.project_path not in self.pinned_paths:
                to_remove.append(session_id)

        for session_id in to_remove:
            logger.debug(f"Removing stale session: {session_id}")
            del self.sessions[session_id]

    def _get_activity_timeout(self) -> int:
        """Get activity timeout from user settings or config defaults."""
        if self.user_settings:
            return self.user_settings.get("activity_timeout")
        return self.config.defaults.get('activityTimeout', 60)

    @property
    def has_activity(self) -> bool:
        """Check if there's any current activity."""
        return any(s.is_active or s.active_tool for s in self.sessions.values())

    @property
    def is_idle(self) -> bool:
        """Check if system has been idle."""
        if self.user_settings:
            idle_timeout = self.user_settings.get("idle_timeout")
        else:
            idle_timeout = self.config.defaults.get('idleTimeout', 15)
        return time.time() - self.last_activity_time > idle_timeout
