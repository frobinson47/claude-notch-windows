# Changelog

All notable changes to Claude Code Notch for Windows will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-08

### Added
- Initial release of Claude Code Notch for Windows
- HTTP server listening on port 27182 for Claude Code events
- System tray icon with dynamic color-coded status
- Floating overlay window with session cards
- 3x2 grid activity indicator with animations
- Semantic design system (7 categories, 9 patterns, 9 colors)
- State management for sessions and tools
- Token usage tracking and context window percentage
- Session pinning/unpinning
- PowerShell hooks for Claude Code integration
- Automatic setup manager for hook installation
- Multi-session support
- Auto-hide on idle (15 second timeout)
- Stale session cleanup (60 second timeout)
- Custom Claude Code commands (/send-to-notch, /remove-from-notch)
- Comprehensive logging to AppData
- Full documentation (README, INSTALL, PROJECT_SUMMARY)
- MIT License

### Features by Component

#### HTTP Server
- Event routes: /hook, /pin, /unpin, /health, /status
- JSON payload parsing
- Thread-based non-blocking execution
- Fire-and-forget event handling

#### State Manager
- Session state tracking
- Tool tracking with display names
- Token usage accumulation
- Context percentage calculation
- Qt signal emission for UI updates
- Semantic configuration loading

#### Tray Icon
- Dynamic icon generation with activity color
- Rich tooltip with session info
- Context menu (overlay, settings, setup, about, quit)
- Double-click to toggle overlay
- Periodic updates (1 second interval)

#### Overlay Window
- Transparent, frameless window
- Session cards with project info
- Activity indicators with semantic animations
- Tool status and context display
- Draggable positioning
- Auto-show on activity, auto-hide on idle

#### Setup Manager
- Automatic hook installation
- Settings.json modification
- PowerShell script copying
- Custom command registration

#### PowerShell Hooks
- notch-hook.ps1 - Main event handler
- send-to-notch.ps1 - Pin session
- remove-from-notch.ps1 - Unpin sessions
- Fire-and-forget HTTP POST
- Error-tolerant execution

### Configuration
- notch-config.json with semantic design system
- Tool-to-category mappings
- Animation pattern definitions
- Color palette (hex + RGB)
- Attention levels (opacity ranges)
- Duration evolution (speed multipliers)
- Default timeouts and behaviors

### Documentation
- README.md - User guide and features
- INSTALL.md - Step-by-step installation
- PROJECT_SUMMARY.md - Technical overview
- CHANGELOG.md - This file
- LICENSE - MIT License

### Technical Details
- Python 3.8+ compatibility
- PySide6 for GUI framework
- HTTP server on port 27182
- Logs to %APPDATA%\claude-notch-windows\logs
- Config in %APPDATA%\claude-notch-windows
- Hooks in %APPDATA%\claude-notch-windows\hooks

## [1.1.0] - 2026-02-13

### Added
- **Attention levels**: Configurable opacity ranges (peripheral/ambient/focal/urgent) per activity category, driven by `notch-config.json`
- **Duration evolution**: Animations gradually slow for long-running tools through normal/extended/long/stuck speed tiers
- **Context progress bar**: Threshold-colored bar (green < 50%, amber 50-80%, red > 80%) showing context window usage per session
- **Permission mode badge**: Overlay status text shows `[plan]`, `[bypass]`, etc. for non-default permission modes
- **Notification balloons**: Tray balloon notifications for Claude Code `Notification` events
- **`/status` API endpoint**: `GET /status` returns real-time JSON with session data, active tools, and idle state
- **Fade animations**: Overlay window uses QPropertyAnimation for smooth show/hide transitions (200ms InOutCubic)
- **Reset Position**: Tray menu item to snap overlay back to configured corner after dragging
- **Test suite**: 55 unit tests (pytest) covering NotchConfig, StateManager event handling, ActiveTool/SessionState dataclasses, and UserSettings validation/persistence
- **Tray icon dirty checking**: Cached `_last_icon_color`/`_last_icon_text`/`_last_tooltip` to skip redundant icon rebuilds

### Fixed
- **Breathe animation**: Was static — now uses wall-clock sinusoidal modulation (`math.sin(time.time() * 2.0)`) for frame-rate-independent ~3s breathing cycle
- **Overlay drag snap-back**: Overlay no longer resets to corner on state updates after user drags it; uses `_user_dragged` flag with screen bounds clamping
- **Thread safety**: HTTP handler callbacks now dispatch to Qt main thread via `QTimer.singleShot(0, ...)` instead of direct cross-thread signal emission
- **Single-instance detection**: Port binding error (errno 10048/WSAEADDRINUSE) provides clear "another instance running" message instead of generic error
- **Duration evolution jitter**: `set_pattern` only called when duration level changes (cached `_last_duration_level`), preventing animation restarts every second
- **Opacity slider**: Now displays percentage (0-100%) instead of raw 0-255 value

### Changed
- `requirements.txt` now includes `pytest>=7.0`
- `overlay_window.py`: `set_pattern()` accepts `attention_config` parameter
- `state_manager.py`: `ActiveTool` dataclass has new `attention` field
- `http_server.py`: Supports `status_callback` for `/status` endpoint

## [Unreleased]

### Planned Features
- Custom icon files (instead of generated)
- Token usage statistics panel
- Theme system (light/dark mode)
- Multi-monitor smart positioning
- Auto-update system
- Global hotkey for show/hide overlay

### Known Issues
- Animation smoothness not as high as macOS version
- Limited error recovery in some edge cases
- Icon quality could be improved

---

[1.0.0]: https://github.com/yourusername/claude-notch-windows/releases/tag/v1.0.0
