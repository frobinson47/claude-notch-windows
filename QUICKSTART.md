# Quick Start Guide

Get Claude Code Notch for Windows running in 5 minutes.

## Prerequisites

- ✅ Windows 10 or 11
- ✅ Python 3.8+ installed
- ✅ Claude Code CLI installed and working

## Installation (3 Steps)

### 1. Install Dependencies

Open PowerShell or Command Prompt in the project directory:

```bash
cd "d:\Claude Code Repo\python_scripts\utilities\claude-notch-windows"
pip install -r requirements.txt
```

**Expected output:**
```
Collecting PySide6>=6.5.0
  Downloading PySide6-6.x.x...
Successfully installed PySide6-6.x.x ...
```

### 2. Run the Application

**Option A - Using launcher (recommended):**
```bash
run.bat
```

**Option B - Using Python directly:**
```bash
python src/main.py
```

**Expected output:**
```
Starting Claude Code Notch for Windows...
Configuration loaded
State manager created
HTTP server started on port 27182
Overlay window created
System tray icon created
Application initialized successfully
Application running
```

**You should see:** An orange/gray circular icon in your system tray (bottom-right corner)

### 3. Setup Hooks

1. **Find the tray icon** - Look in your system tray (may be in the overflow area - click the ^ icon)
2. **Right-click the icon**
3. **Click "Setup Hooks"**
4. **Wait for success notification** - "Claude Code hooks installed successfully!"

✅ **Done!** The app is now running and monitoring Claude Code activity.

## Verify It's Working

### Test 1: Check the Server

Open a new PowerShell window:

```powershell
Invoke-RestMethod -Uri "http://localhost:27182/health" -Method Get
```

**Expected:** `{"status": "running"}`

### Test 2: Use Claude Code

Open Claude Code and ask it to do something:

```bash
# Example command
claude-code

# Ask Claude to do something
> Can you read the README.md file in this directory?
```

**Watch the tray icon:**
- Should change color (cyan for reading)
- Tooltip should show "Perusing - YourProject"

### Test 3: View the Overlay

**Double-click the tray icon** to show the floating overlay window.

You should see:
- A dark transparent window
- Session card with project name
- 3x2 grid animation (colored squares)
- Tool status ("Perusing", "Crafting", etc.)

## Usage

### Tray Icon

**Colors:**
- 🟠 Orange = Thinking
- 🔵 Cyan = Reading/Searching
- 🟢 Green = Writing
- 🟡 Amber = Editing
- 🔴 Red = Executing commands
- 🟣 Violet = Web/API calls
- 🔵 Blue = Needs attention
- ⚪ Gray = Idle

**Tooltip:** Hover over icon to see current activity

**Menu:** Right-click for options

### Overlay Window

**Show/Hide:** Double-click tray icon

**Move:** Click and drag the window

**Auto-hide:** Window hides automatically after 15 seconds of inactivity

### Custom Commands

In Claude Code, use:

```bash
# Pin current session to always show in overlay
/send-to-notch

# Unpin all sessions
/remove-from-notch
```

## Troubleshooting

### "Port 27182 already in use"

Someone else is using the port. Find and kill the process:

```powershell
# Find the process
netstat -ano | findstr :27182

# Kill it (replace <PID> with actual number)
taskkill /PID <PID> /F
```

### "PySide6 won't install"

Update pip first:

```powershell
python -m pip install --upgrade pip
pip install PySide6
```

### "Hooks not working"

Check if they're installed:

```powershell
type %USERPROFILE%\.claude\settings.json
```

Should contain entries with `claude-notch-windows`. If not, run Setup Hooks again.

### "Can't find tray icon"

1. Check system tray overflow (click ^ in taskbar)
2. Check if app is running: `tasklist | findstr python`
3. Check logs: `%APPDATA%\claude-notch-windows\logs\claude-notch.log`

## What's Next?

- 📖 Read [README.md](README.md) for detailed features
- 🔧 Read [INSTALL.md](INSTALL.md) for advanced setup
- ⚙️ Customize [config/notch-config.json](config/notch-config.json) for your preferences
- 🚀 Set up auto-start on Windows boot (see INSTALL.md)

## Support

- **Logs:** `%APPDATA%\claude-notch-windows\logs\claude-notch.log`
- **Config:** `%APPDATA%\claude-notch-windows\`
- **Claude Settings:** `%USERPROFILE%\.claude\settings.json`

---

**Enjoy real-time visibility into Claude Code! 🎉**
