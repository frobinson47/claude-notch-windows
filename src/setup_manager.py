"""
Setup Manager for Claude Code Notch.
Handles hook installation and Claude Code configuration.
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SetupManager:
    """Manages installation of hooks and configuration."""

    def __init__(self):
        """Initialize setup manager."""
        # Paths
        self.home_dir = Path.home()
        self.claude_dir = self.home_dir / ".claude"
        self.config_dir = self.home_dir / "AppData" / "Roaming" / "claude-notch-windows"
        self.hooks_dir = self.config_dir / "hooks"

        # Source hooks directory (relative to this file)
        self.source_hooks_dir = Path(__file__).parent.parent / "hooks"

        # Settings file
        self.settings_file = self.claude_dir / "settings.json"

    def install_hooks(self) -> bool:
        """
        Install Claude Code hooks.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting hook installation...")

            # Create directories
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.hooks_dir.mkdir(parents=True, exist_ok=True)
            self.claude_dir.mkdir(parents=True, exist_ok=True)

            # Copy hook scripts
            self._copy_hooks()

            # Update settings.json
            self._update_settings()

            logger.info("Hook installation complete!")
            return True

        except Exception as e:
            logger.error(f"Hook installation failed: {e}", exc_info=True)
            return False

    def _copy_hooks(self):
        """Copy hook scripts to config directory."""
        logger.info("Copying hook scripts...")

        hook_files = [
            # Python hooks (primary)
            "notch-hook.py",
            "send-to-notch.py",
            "remove-from-notch.py",
            # PowerShell hooks (kept for backward compat)
            "notch-hook.ps1",
            "send-to-notch.ps1",
            "remove-from-notch.ps1",
        ]

        for filename in hook_files:
            source = self.source_hooks_dir / filename
            dest = self.hooks_dir / filename

            if not source.exists():
                logger.warning(f"Source hook not found: {source}")
                continue

            shutil.copy2(source, dest)
            logger.debug(f"Copied {filename} to {dest}")

        logger.info(f"Hooks copied to {self.hooks_dir}")

    @staticmethod
    def _get_hook_command(py_script: str, ps1_script: str) -> str:
        """Build the hook command, preferring Python for speed.

        Falls back to PowerShell with optimized flags if Python isn't
        resolvable (e.g. PyInstaller bundle without clear sys.executable).
        """
        python_exe = sys.executable
        # Sanity-check: sys.executable should point to a real python
        if python_exe and os.path.isfile(python_exe) and "python" in os.path.basename(python_exe).lower():
            return f'"{python_exe}" "{py_script}"'

        # Fallback: PowerShell with optimized startup flags
        return (
            f'powershell.exe -NoProfile -NoLogo -NonInteractive '
            f'-ExecutionPolicy Bypass -File "{ps1_script}"'
        )

    def _update_settings(self):
        """Update Claude Code settings.json to register hooks."""
        logger.info("Updating Claude Code settings...")

        # Load existing settings or create new
        if self.settings_file.exists():
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
            logger.debug("Loaded existing settings.json")
        else:
            settings = {}
            logger.debug("Creating new settings.json")

        # Ensure hooks section exists
        if "hooks" not in settings:
            settings["hooks"] = {}

        # Build hook command (Python primary, PowerShell fallback)
        py_hook = str(self.hooks_dir / "notch-hook.py").replace("\\", "/")
        ps1_hook = str(self.hooks_dir / "notch-hook.ps1").replace("\\", "/")
        hook_command = self._get_hook_command(py_hook, ps1_hook)

        # Events to hook
        events = [
            "PreToolUse",
            "PostToolUse",
            "Stop",
            "SubagentStop",
            "SessionStart",
            "SessionEnd",
            "UserPromptSubmit",
            "Notification"
        ]

        # Add hooks for each event, preserving existing hooks
        notch_hook_entry = {
            "matcher": "",
            "hooks": [
                {
                    "type": "command",
                    "command": hook_command
                }
            ]
        }

        # Marker strings to detect our previously-installed hooks (old or new)
        notch_markers = ["notch-hook.ps1", "notch-hook.py"]

        for event in events:
            if event not in settings["hooks"]:
                settings["hooks"][event] = []

            existing = settings["hooks"][event]

            # Remove any stale notch hooks (e.g. old PS1 version) before adding new
            existing[:] = [
                entry for entry in existing
                if not any(marker in json.dumps(entry) for marker in notch_markers)
            ]

            existing.append(notch_hook_entry)

        # Add custom commands for pin/unpin
        if "commands" not in settings:
            settings["commands"] = {}

        py_pin = str(self.hooks_dir / "send-to-notch.py").replace("\\", "/")
        ps1_pin = str(self.hooks_dir / "send-to-notch.ps1").replace("\\", "/")
        py_unpin = str(self.hooks_dir / "remove-from-notch.py").replace("\\", "/")
        ps1_unpin = str(self.hooks_dir / "remove-from-notch.ps1").replace("\\", "/")

        settings["commands"]["send-to-notch"] = {
            "description": "Pin current session to Windows Notch display",
            "script": self._get_hook_command(py_pin, ps1_pin)
        }

        settings["commands"]["remove-from-notch"] = {
            "description": "Unpin all sessions from Windows Notch display",
            "script": self._get_hook_command(py_unpin, ps1_unpin)
        }

        # Save settings
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        logger.info(f"Settings updated: {self.settings_file}")

    def uninstall_hooks(self) -> bool:
        """
        Uninstall Claude Code hooks.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting hook uninstallation...")

            # Remove from settings.json
            if self.settings_file.exists():
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)

                # Remove hook entries (match both Python and PowerShell variants)
                notch_markers = ["notch-hook.ps1", "notch-hook.py"]
                if "hooks" in settings:
                    for event, entries in settings["hooks"].items():
                        if isinstance(entries, list):
                            entries[:] = [
                                entry for entry in entries
                                if not any(m in json.dumps(entry) for m in notch_markers)
                            ]

                # Remove custom commands
                if "commands" in settings:
                    settings["commands"].pop("send-to-notch", None)
                    settings["commands"].pop("remove-from-notch", None)

                # Save settings
                with open(self.settings_file, 'w') as f:
                    json.dump(settings, f, indent=2)

                logger.info("Hooks removed from settings.json")

            # Optionally remove hook files
            # (keeping them for now in case user wants to reinstall)

            logger.info("Hook uninstallation complete!")
            return True

        except Exception as e:
            logger.error(f"Hook uninstallation failed: {e}", exc_info=True)
            return False

    def is_installed(self) -> bool:
        """Check if hooks are installed."""
        if not self.settings_file.exists():
            return False

        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)

            # Match either Python or PowerShell hook scripts
            notch_markers = ["notch-hook.ps1", "notch-hook.py"]

            # Check if any hooks point to our script
            if "hooks" in settings:
                settings_str = json.dumps(settings["hooks"])
                if any(m in settings_str for m in notch_markers):
                    return True

            return False

        except Exception:
            return False


if __name__ == "__main__":
    # Test setup
    logging.basicConfig(level=logging.DEBUG)

    setup = SetupManager()
    print(f"Hooks installed: {setup.is_installed()}")

    if not setup.is_installed():
        print("\nInstalling hooks...")
        success = setup.install_hooks()
        print(f"Installation {'successful' if success else 'failed'}")
