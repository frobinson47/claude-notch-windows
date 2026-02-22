# Upgrade Roadmap

Status: DONE = shipped, READY = reviewed & approved, SKIP = already covered

---

## Sound & Notifications

| Feature | What it does | Effort | Status | Review Notes |
|---------|-------------|--------|--------|-------------|
| Sound cues | System beeps for errors, attention, session end (winsound) | Small | DONE | Shipped with 2s debounce, per-type cooldown, settings toggles |
| Error flash | Red flash overlay on session card for Bash failures | Small | DONE | Shipped with QPropertyAnimation fade, exit-code-first detection |
| Desktop toasts | Windows native notifications via winrt for key events | Small | DONE | Shipped: toast_requested Signal with shared cooldown, wired through QSystemTrayIcon.showMessage. toasts_enabled toggle in Settings > Notifications |
| Discord/Slack webhook | POST event summaries to a user-configured webhook URL | Medium | READY | Async dispatcher required (never UI thread). Store secrets via Windows Credential Manager. Redacted payloads by default. Rate limiting/429 handling |

## Stats & Insights

| Feature | What it does | Effort | Status | Review Notes |
|---------|-------------|--------|--------|-------------|
| Session statistics | Track tool usage counts, time per category, persist to JSON | Medium | READY | Scoped v1: aggregate counters + coarse category time. Bounded retention, schema versioning, atomic writes. No raw event timelines |
| Token estimation | Display estimated token usage | Medium | SKIP | Already implemented: _update_token_usage parses transcript, ContextRing shows usage arc. Only hardening needed (formula docs, parser robustness tests) |

## System Integration

| Feature | What it does | Effort | Status | Review Notes |
|---------|-------------|--------|--------|-------------|
| Auto-start on boot | Add/remove Windows startup registry entry from settings | Small | DONE | Already shipped in UserSettings + SettingsDialog |
| Global hotkey | Toggle overlay visibility with configurable shortcut | Small | DONE | Shipped: Win32 RegisterHotKey via ctypes, daemon GetMessage thread, Signal bridge. Default Ctrl+Shift+N, configurable in Settings > Behavior. Non-fatal on failure |
| Click-to-focus | Click a session card to bring that terminal to foreground | Medium | READY | Constrained v1: explicit HWND/PID binding at session start, not title heuristics. Accept SetForegroundWindow limitations. Ship behind feature flag |
| Multi-monitor | Settings dropdown to pick which display | Small | DONE | Shipped: target_monitor setting, QComboBox populated from QGuiApplication.screens(), fallback to primary on unplug/invalid name |

## Visual & Customization

| Feature | What it does | Effort | Status | Review Notes |
|---------|-------------|--------|--------|-------------|
| Mini mode | Collapsed single-line bar showing just color + project name | Medium | READY | Presentation-layer variant with shared session model. Phase 1: static mini, no heavy effects. Explicit UI state machine for transitions |
| Timeline strip | Thin color bar showing last N tool changes as a history | Medium | READY | Static, non-animated, max 10 segments from existing recent_tools. Coalesce consecutive same-category. Enforce 1px minimum segment width |
| Per-project colors | Map project names to custom overlay accent colors in config | Small | DONE | Shipped: project_colors dict in settings, precedence: project > tool > slate. Text editor in Settings > Overlay with color validation |
| Theme presets | Light/dark/custom background + text color schemes | Medium | READY | Limit to Dark/Light/Custom. Tokenize hardcoded color literals. Config migration for existing users. Contrast guardrails |

---

## Suggested Priority (by value/effort)

1. ~~Global hotkey~~ DONE
2. ~~Multi-monitor~~ DONE
3. ~~Per-project colors~~ DONE
4. Timeline strip (Medium, leverages existing recent_tools)
5. Mini mode (Medium, significant UX win)
6. Session statistics (Medium, extends existing tracking)
7. ~~Desktop toasts~~ DONE
8. Theme presets (Medium, quality-of-life)
9. Click-to-focus (Medium, high complexity/reliability risk)
10. Discord/Slack webhook (Medium, security/async complexity)

All features received CONDITIONAL GO from Codex architecture review (2026-02-21).
Zero NO-GOs. Each has specific prerequisites documented in Review Notes.
