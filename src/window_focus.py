"""
Standalone Win32 API module for terminal window focusing.

Uses ctypes to interact with Win32 APIs for finding and focusing
terminal windows by walking the process tree. No Qt or project
dependencies required.
"""

import ctypes
import ctypes.wintypes
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Win32 API bindings
# ---------------------------------------------------------------------------

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Constants
TH32CS_SNAPPROCESS = 0x00000002
SW_RESTORE = 9
INVALID_HANDLE_VALUE = -1


class PROCESSENTRY32(ctypes.Structure):
    """PROCESSENTRY32 structure for process snapshots."""

    _fields_ = [
        ("dwSize", ctypes.wintypes.DWORD),
        ("cntUsage", ctypes.wintypes.DWORD),
        ("th32ProcessID", ctypes.wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", ctypes.wintypes.DWORD),
        ("cntThreads", ctypes.wintypes.DWORD),
        ("th32ParentProcessID", ctypes.wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


# Function signatures
EnumWindows = user32.EnumWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
)
EnumWindows.argtypes = [WNDENUMPROC, ctypes.wintypes.LPARAM]
EnumWindows.restype = ctypes.wintypes.BOOL

GetWindowThreadProcessId = user32.GetWindowThreadProcessId
IsWindowVisible = user32.IsWindowVisible
SetForegroundWindow = user32.SetForegroundWindow
IsWindow = user32.IsWindow
ShowWindow = user32.ShowWindow

CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
Process32First = kernel32.Process32First
Process32Next = kernel32.Process32Next
CloseHandle = kernel32.CloseHandle


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_process_tree():
    """Build PID -> parent PID mapping using a process snapshot."""
    pid_to_parent = {}
    snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        return pid_to_parent
    try:
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        if Process32First(snapshot, ctypes.byref(entry)):
            while True:
                pid_to_parent[entry.th32ProcessID] = entry.th32ParentProcessID
                if not Process32Next(snapshot, ctypes.byref(entry)):
                    break
    finally:
        CloseHandle(snapshot)
    return pid_to_parent


def _find_window_for_pid(target_pid):
    """Find a visible top-level window owned by *target_pid*."""
    result = []

    def callback(hwnd, lparam):
        pid = ctypes.wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == target_pid and IsWindowVisible(hwnd):
            result.append(hwnd)
            return False  # Stop enumeration
        return True  # Continue

    EnumWindows(WNDENUMPROC(callback), 0)
    return result[0] if result else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_terminal_hwnd(pid: int) -> Optional[int]:
    """Find the terminal window handle by walking up the process tree.

    Starting from *pid*, walks up through parent processes and checks
    each level for a visible top-level window.  Returns the first
    matching HWND, or ``None`` if no window is found within 10 levels.

    Args:
        pid: The process ID to start the search from.

    Returns:
        The window handle (HWND) as an int, or None.
    """
    try:
        pid_to_parent = _build_process_tree()
        current_pid = pid

        for level in range(10):
            hwnd = _find_window_for_pid(current_pid)
            if hwnd is not None:
                logger.debug(
                    "Found terminal window hwnd=%s for pid=%s at level %d",
                    hwnd,
                    current_pid,
                    level,
                )
                return hwnd

            # Walk up to the parent process
            parent_pid = pid_to_parent.get(current_pid)
            if parent_pid is None or parent_pid == current_pid:
                # No parent found or self-referencing — stop
                break
            current_pid = parent_pid

        logger.debug("No terminal window found for pid=%s after tree walk", pid)
        return None
    except Exception:
        logger.exception("Error finding terminal window for pid=%s", pid)
        return None


def focus_window(hwnd: int) -> bool:
    """Bring the window identified by *hwnd* to the foreground.

    Un-minimises the window with ``SW_RESTORE`` first, then calls
    ``SetForegroundWindow``.

    Args:
        hwnd: The window handle to focus.

    Returns:
        True if ``SetForegroundWindow`` succeeded, False otherwise.
    """
    try:
        if not IsWindow(hwnd):
            logger.debug("focus_window: hwnd=%s is not a valid window", hwnd)
            return False

        ShowWindow(hwnd, SW_RESTORE)
        result = SetForegroundWindow(hwnd)
        if result:
            logger.debug("Successfully focused window hwnd=%s", hwnd)
        else:
            logger.debug("SetForegroundWindow returned False for hwnd=%s", hwnd)
        return bool(result)
    except Exception:
        logger.exception("Error focusing window hwnd=%s", hwnd)
        return False


def is_window_valid(hwnd: int) -> bool:
    """Check whether *hwnd* refers to an existing window.

    Args:
        hwnd: The window handle to validate.

    Returns:
        True if the window exists, False otherwise.
    """
    try:
        return bool(IsWindow(hwnd))
    except Exception:
        logger.exception("Error checking window validity for hwnd=%s", hwnd)
        return False
