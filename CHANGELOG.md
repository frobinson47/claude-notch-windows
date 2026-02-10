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
- PyQt5 for GUI framework
- HTTP server on port 27182
- Logs to %APPDATA%\claude-notch-windows\logs
- Config in %APPDATA%\claude-notch-windows
- Hooks in %APPDATA%\claude-notch-windows\hooks

## [Unreleased]

### Planned Features
- Settings dialog GUI
- Custom icon files (instead of generated)
- Windows toast notifications
- Token usage statistics panel
- Theme system (light/dark mode)
- Multi-monitor smart positioning
- PyInstaller standalone executable
- Auto-update system
- Performance optimizations

### Known Issues
- Animation smoothness not as high as macOS version
- No unit tests yet
- Limited error recovery in some edge cases
- Icon quality could be improved
- No GUI for configuration (JSON editing only)

---

[1.0.0]: https://github.com/yourusername/claude-notch-windows/releases/tag/v1.0.0
