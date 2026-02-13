# Installation Guide - Claude Code Notch for Windows

## Quick Start

1. **Install Python** (if not already installed)
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation
   - Minimum version: Python 3.8

2. **Install Dependencies**
   ```bash
   cd "d:\Claude Code Repo\python_scripts\utilities\claude-notch-windows"
   pip install -r requirements.txt
   ```

3. **Run the Application**

   **Option A: Using the launcher (recommended)**
   ```bash
   run.bat
   ```

   **Option B: Using Python directly**
   ```bash
   python src/main.py
   ```

4. **Setup Claude Code Hooks**
   - Once the app is running, look for the tray icon in your system tray
   - Right-click the icon
   - Select "Setup Hooks"
   - You should see a success notification

5. **Verify Installation**
   - Open Claude Code CLI
   - Start using Claude (ask it to do something)
   - You should see the tray icon change color
   - Double-click the tray icon to show the overlay window

## Detailed Setup

### System Requirements

- **OS:** Windows 10 or Windows 11
- **Python:** 3.8 or higher
- **Claude Code:** Latest version installed and configured
- **Disk Space:** ~50 MB for Python dependencies

### Step-by-Step Installation

#### 1. Verify Python Installation

Open PowerShell or Command Prompt and run:

```bash
python --version
```

You should see something like `Python 3.11.x`. If not, install Python first.

#### 2. Navigate to Project Directory

```bash
cd "d:\Claude Code Repo\python_scripts\utilities\claude-notch-windows"
```

#### 3. Create Virtual Environment (Optional but Recommended)

```bash
python -m venv venv
venv\Scripts\activate
```

#### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install PySide6, which is the only dependency.

#### 5. Run the Application

```bash
python src\main.py
```

You should see log messages indicating the app started successfully:

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

#### 6. Setup Hooks

**Manual Method:**

1. Right-click the system tray icon (look for a colored circle)
2. Click "Setup Hooks"
3. Wait for the success notification

**Verify Hook Installation:**

Check if `~/.claude/settings.json` contains hook entries:

```bash
type %USERPROFILE%\.claude\settings.json
```

You should see entries like:

```json
{
  "hooks": {
    "PreToolUse": "powershell.exe -ExecutionPolicy Bypass -File \"C:/Users/YourName/AppData/Roaming/claude-notch-windows/hooks/notch-hook.ps1\"",
    "PostToolUse": "powershell.exe -ExecutionPolicy Bypass -File \"C:/Users/YourName/AppData/Roaming/claude-notch-windows/hooks/notch-hook.ps1\"",
    ...
  }
}
```

### Testing

1. **Test HTTP Server**

   Open a new PowerShell window:

   ```powershell
   Invoke-RestMethod -Uri "http://localhost:27182/health" -Method Get
   ```

   Should return: `{"status": "running"}`

2. **Test Hook Manually**

   ```powershell
   $payload = @{eventType="PreToolUse"; sessionId="test"; cwd="C:\test"; tool="Read"} | ConvertTo-Json
   Invoke-RestMethod -Uri "http://localhost:27182/hook" -Method Post -Body $payload -ContentType "application/json"
   ```

   You should see the tray icon change color.

3. **Test with Claude Code**

   Open Claude Code and ask it to do something:

   ```bash
   claude-code
   > Can you read the README.md file?
   ```

   Watch the tray icon change colors as Claude works.

## Running on Startup (Optional)

### Method 1: Task Scheduler (Recommended)

1. Open Task Scheduler (`taskschd.msc`)
2. Click "Create Task"
3. **General tab:**
   - Name: Claude Code Notch
   - Check "Run whether user is logged on or not"
   - Check "Run with highest privileges"
4. **Triggers tab:**
   - New → Begin the task: At log on
5. **Actions tab:**
   - New → Action: Start a program
   - Program: `pythonw.exe` (or `python.exe`)
   - Arguments: `src\main.py`
   - Start in: `d:\Claude Code Repo\python_scripts\utilities\claude-notch-windows`
6. Click OK

### Method 2: Startup Folder

1. Create a shortcut to `run.bat`
2. Press `Win+R`, type `shell:startup`, press Enter
3. Copy the shortcut to the Startup folder

## Troubleshooting

### Port 27182 Already in Use

```bash
# Find the process using the port
netstat -ano | findstr :27182

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

### PowerShell Execution Policy Issues

If hooks fail due to execution policy:

```powershell
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Tray Icon Not Showing

- Check if the app is running: Look for `python.exe` in Task Manager
- Check system tray overflow area (click the ^ icon in the taskbar)
- Check logs: `%APPDATA%\claude-notch-windows\logs\claude-notch.log`

### Overlay Window Not Appearing

- Double-click the tray icon to toggle visibility
- Make sure you have an active Claude Code session
- Check if the window is off-screen (try moving it back: drag from tray menu)

### Hooks Not Firing

1. Verify hooks are installed: `type %USERPROFILE%\.claude\settings.json`
2. Test PowerShell hook manually (see Testing section above)
3. Check if Claude Code is using the correct settings file
4. Restart Claude Code after installing hooks

### Dependencies Won't Install

```bash
# Upgrade pip first
python -m pip install --upgrade pip

# Install with verbose output
pip install -v -r requirements.txt

# If PySide6 fails, try installing separately
pip install PySide6
```

## Uninstallation

1. **Stop the application** (right-click tray → Quit)

2. **Remove hooks** (optional)
   - Edit `%USERPROFILE%\.claude\settings.json`
   - Remove entries pointing to `claude-notch-windows`

3. **Delete files**
   ```bash
   # Application files
   rmdir /s "d:\Claude Code Repo\python_scripts\utilities\claude-notch-windows"

   # Config and logs
   rmdir /s "%APPDATA%\claude-notch-windows"
   ```

4. **Remove from startup** (if configured)
   - Task Scheduler: Delete the task
   - Startup folder: Delete the shortcut

## Next Steps

- Read [README.md](README.md) for usage instructions
- Customize colors/animations in `config/notch-config.json`
- Report issues or contribute on GitHub

---

**Need Help?** Check the logs at `%APPDATA%\claude-notch-windows\logs\claude-notch.log`
