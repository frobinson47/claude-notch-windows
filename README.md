# Claude Code Notch for Windows

A Windows companion app for Claude Code CLI that displays real-time AI activity in your system tray and floating overlay.

## Features

- **System Tray Integration** - Always-visible status indicator
- **Floating Overlay Window** - Beautiful animated activity display
- **Real-time Activity Tracking** - See what Claude is doing (Reading, Writing, Executing, etc.)
- **Token Usage Monitoring** - Track context window usage
- **Session Management** - Pin/unpin sessions for persistent display
- **Semantic Design System** - Color-coded activities with smooth animations

## Installation

### Requirements

- Windows 10/11
- Python 3.8 or higher
- Claude Code CLI installed

### Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python src/main.py
   ```

3. **Install Claude Code hooks:**
   - Right-click the system tray icon
   - Select "Setup Hooks"
   - This will configure Claude Code to send events to the Windows app

## Usage

### System Tray

The app runs in your system tray and shows:
- **Icon Color** - Current activity type (orange=thinking, cyan=reading, green=writing, etc.)
- **Tooltip** - Current tool and project info
- **Context Menu** - Access settings, overlay toggle, and setup

### Overlay Window

The floating overlay shows detailed activity:
- **Session Cards** - One card per active Claude session
- **Activity Indicator** - 3x2 grid animation showing current pattern
- **Project Info** - Current project name and working directory
- **Tool Status** - What Claude is currently doing
- **Context Percentage** - How much of the context window is used

**Controls:**
- **Double-click tray icon** - Show/hide overlay
- **Drag overlay** - Reposition the window
- **Right-click tray** - Access menu

### Custom Commands

Once hooks are installed, you can use these commands in Claude Code:

```bash
# Pin current session to always show in overlay
/send-to-notch

# Unpin all sessions
/remove-from-notch
```

## Activity Colors

The app uses a semantic color system:

- **Cyan** (Observe) - Reading, searching (Read, Glob, Grep)
- **Orange** (Think) - Processing, reasoning (internal work)
- **Green** (Create) - Writing new files (Write)
- **Amber** (Transform) - Editing existing files (Edit)
- **Red** (Execute) - Running commands (Bash)
- **Violet** (Connect) - External APIs, web (WebFetch, WebSearch)
- **Blue** (Interact) - Needs attention (AskUserQuestion)
- **Gray** (Idle) - No current activity

## Configuration

The app's behavior is controlled by `config/notch-config.json`:

- **Tools** - Display names for each tool type
- **Categories** - Color and animation patterns
- **Patterns** - Animation sequences
- **Defaults** - Timeouts and behavior settings

## File Structure

```
claude-notch-windows/
├── src/
│   ├── main.py              # Application entry point
│   ├── http_server.py       # HTTP server for receiving events
│   ├── state_manager.py     # Session and tool state management
│   ├── tray_icon.py         # System tray icon
│   ├── overlay_window.py    # Floating overlay UI
│   └── setup_manager.py     # Hook installation
├── hooks/
│   ├── notch-hook.ps1       # Main event hook
│   ├── send-to-notch.ps1    # Pin session command
│   └── remove-from-notch.ps1 # Unpin command
├── config/
│   └── notch-config.json    # Semantic design configuration
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## How It Works

1. **Claude Code** executes PowerShell hooks on various events (PreToolUse, PostToolUse, etc.)
2. **PowerShell hooks** send JSON payloads to `http://localhost:27182`
3. **HTTP server** receives events and passes them to the state manager
4. **State manager** updates session states and emits Qt signals
5. **UI components** (tray icon, overlay) react to state changes and update display

## Troubleshooting

### Hooks not working

1. Check that hooks are installed: Right-click tray → "Setup Hooks"
2. Verify `~/.claude/settings.json` contains hook entries
3. Check logs: `%APPDATA%\claude-notch-windows\logs\claude-notch.log`

### Server won't start

- Check if port 27182 is already in use
- Run `netstat -ano | findstr :27182` to find conflicting processes

### Overlay not showing

- Check if you have active Claude Code sessions
- Overlay auto-hides when idle for 15 seconds
- Double-click tray icon to manually show/hide

## Development

### Running from source

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python src/main.py

# Test HTTP server
python src/http_server.py

# Test state manager
python src/state_manager.py

# Test setup manager
python src/setup_manager.py
```

### Building standalone executable

You can use PyInstaller to create a standalone .exe:

```bash
pip install pyinstaller

pyinstaller --onefile --windowed --icon=resources/icon.ico src/main.py
```

## Credits

Inspired by [cookinn.notch](https://github.com/cookinn/notch) for macOS by [@cookinn](https://github.com/cookinn).

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or PR on GitHub.

---

**Note:** This is a Windows port of the macOS cookinn.notch app. While it maintains the same semantic design philosophy and feature set, it's adapted for Windows using PyQt5 instead of Swift/SwiftUI.
