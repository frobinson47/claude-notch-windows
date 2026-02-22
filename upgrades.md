# Upgrade Roadmap

Status: DONE = shipped, READY = reviewed & approved, SKIP = already covered

---

## Sound & Notifications

| Feature | What it does | Effort | Status | Review Notes |
|---------|-------------|--------|--------|-------------|
| Sound cues | System beeps for errors, attention, session end (winsound) | Small | DONE | Shipped with 2s debounce, per-type cooldown, settings toggles |
| Error flash | Red flash overlay on session card for Bash failures | Small | DONE | Shipped with QPropertyAnimation fade, exit-code-first detection |
| Desktop toasts | Windows native notifications via winrt for key events | Small | DONE | Shipped: toast_requested Signal with shared cooldown, wired through QSystemTrayIcon.showMessage. toasts_enabled toggle in Settings > Notifications |
| Discord/Slack webhook | POST event summaries to a user-configured webhook URL | Medium | DONE | Shipped: webhook_dispatcher.py with async threading dispatch, auto-detect Discord/Slack format, 5s rate limiting, 429 retry, redacted payloads. UI in Settings > Notifications with URL field + test button. 10 tests |

## Stats & Insights

| Feature | What it does | Effort | Status | Review Notes |
|---------|-------------|--------|--------|-------------|
| Session statistics | Track tool usage counts, time per category, persist to JSON | Medium | DONE | Shipped: SessionStats module with schema v1, atomic writes, 90-day retention. StateManager records on PostToolUse (excludes _thinking). Stats tab in Settings shows top 10 tools, category time, session count. 11 tests |
| Token estimation | Display estimated token usage | Medium | SKIP | Already implemented: _update_token_usage parses transcript, ContextRing shows usage arc. Only hardening needed (formula docs, parser robustness tests) |

## System Integration

| Feature | What it does | Effort | Status | Review Notes |
|---------|-------------|--------|--------|-------------|
| Auto-start on boot | Add/remove Windows startup registry entry from settings | Small | DONE | Already shipped in UserSettings + SettingsDialog |
| Global hotkey | Toggle overlay visibility with configurable shortcut | Small | DONE | Shipped: Win32 RegisterHotKey via ctypes, daemon GetMessage thread, Signal bridge. Default Ctrl+Shift+N, configurable in Settings > Behavior. Non-fatal on failure |
| Click-to-focus | Click a session card to bring that terminal to foreground | Medium | DONE | Shipped: window_focus.py with Win32 ctypes (EnumWindows, CreateToolhelp32Snapshot, SetForegroundWindow). Hook sends os.getppid() PID, StateManager captures HWND on SessionStart. Cards show pointing cursor + mouseReleaseEvent. click_to_focus toggle in Settings > Behavior. 10 tests |
| Multi-monitor | Settings dropdown to pick which display | Small | DONE | Shipped: target_monitor setting, QComboBox populated from QGuiApplication.screens(), fallback to primary on unplug/invalid name |

## Visual & Customization

| Feature | What it does | Effort | Status | Review Notes |
|---------|-------------|--------|--------|-------------|
| Mini mode | Collapsed single-line bar showing just color + project name | Medium | DONE | Shipped: MiniSessionCard (26px, color dot + project name + status), toggle via Settings > Overlay checkbox and tray menu. _rebuild_cards() switches card type live. 9 tests |
| Timeline strip | Thin color bar showing last N tool changes as a history | Medium | DONE | Shipped: 8px TimelineStrip widget below session card, coalesces consecutive same-category, proportional segments with 1px min width, auto-hides when empty. 6 tests |
| Per-project colors | Map project names to custom overlay accent colors in config | Small | DONE | Shipped: project_colors dict in settings, precedence: project > tool > slate. Text editor in Settings > Overlay with color validation |
| Theme presets | Light/dark/custom background + text color schemes | Medium | DONE | Shipped: themes.py with tokenized Dark/Light presets, generate_dialog_stylesheet replaces hardcoded _DARK_STYLE. Theme combo in Settings > Overlay, overlay + cards + dialog all theme-aware. 17 tests |

---

## Suggested Priority (by value/effort)

1. ~~Global hotkey~~ DONE
2. ~~Multi-monitor~~ DONE
3. ~~Per-project colors~~ DONE
4. ~~Timeline strip~~ DONE
5. ~~Mini mode~~ DONE
6. ~~Session statistics~~ DONE
7. ~~Desktop toasts~~ DONE
8. ~~Theme presets~~ DONE
9. ~~Click-to-focus~~ DONE
10. ~~Discord/Slack webhook~~ DONE

All features received CONDITIONAL GO from Codex architecture review (2026-02-21).
Zero NO-GOs. Each has specific prerequisites documented in Review Notes.
