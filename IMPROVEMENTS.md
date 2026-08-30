# VISION — Documentation Improvements & Feature Roadmap

This document is a deep-dive audit of the current codebase. It lists documentation fixes, missing functions to implement, and architectural improvements — organized by priority.

**Last reviewed:** 2026-08-28  
**Codebase version:** ~17 source files, Python 3.12+, PySide6

---

## ✅ Completed (2026-08-29)

The items below have since been implemented — the roadmap sections further down
predate them and are kept for historical context.

- **CPU/resource reduction:** adaptive physics tick (16 ms moving / 66 ms idle,
  ms-driven so speeds are unchanged), cached screen geometry, and throttled
  monitor subprocess calls (Bluetooth ~30 s, Wi‑Fi/online ~6 s).
- **Clean shutdown:** "Close Companion" now stops the listener/monitor threads
  before quitting (was leaking `QThread`s / hanging).
- **`override:clear` / `override:lock`** TCP commands (fixes stuck override).
- **Consolidated monitoring:** the client is now the single source of truth;
  `main.py` launches one process. Transition events (`wifi_connected`,
  `charged_filled`, mute toggles) moved into the client. The backend daemon is
  now optional/legacy.
- **Wired dead animations:** AI `state:busy|success|error|idle` →
  `waiting`/`review`/`failed`; `need_to_go_bed` bedtime reminder; inactivity
  timer → `very_tired`→`need_rest`→`sleeping`; RAM > 90% reaction;
  `muted`/`unmuted` via optional `pycaw`.
- **Cleanup:** removed dead `mouseMouseMoveEvent`, hoisted `import datetime`.
- **Correction:** `newimage.webp` **is** present in the repo (the "High" blocker
  below is out of date).

---

## Table of Contents

1. [Current Architecture (Deep Dive)](#1-current-architecture-deep-dive)
2. [Documentation Gaps & Fixes](#2-documentation-gaps--fixes)
3. [Functions That Need to Be Added](#3-functions-that-need-to-be-added)
4. [TCP API Expansion](#4-tcp-api-expansion)
5. [Code Quality & Infrastructure](#5-code-quality--infrastructure)
6. [Implementation Priority Matrix](#6-implementation-priority-matrix)

---

## 1. Current Architecture (Deep Dive)

### 1.1 Process Model

```
main.py
  ├── subprocess: python -m src.vision_pet.client   (PySide6 GUI + TCP server)
  └── subprocess: python -m src.vision_pet.backend  (polling daemon, sends TCP commands)
```

Both processes run independently. The client binds `127.0.0.1:5050`; the backend connects as a TCP client via `send_command()`.

### 1.2 Client Internals (`DesktopPet`)

| Subsystem | Class / Module | Interval | Responsibility |
|---|---|---|---|
| Animation engine | `pet_widget.py` | Per-frame timer (100–260 ms) | Spritesheet playback, state transitions via `next` key |
| Physics loop | `pet_widget.py` | 16 ms (~60 FPS) | Gravity, wander AI, boundary clamping, drag |
| TCP listener | `listener.py` (QThread) | Blocking accept (1 s timeout) | Receives `command:value` strings |
| System monitor | `monitor.py` (QThread) | 3.0 s poll | CPU, RAM, battery, Wi‑Fi, Bluetooth |
| Context menu | `pet_widget.py` | On right-click | Manual animation triggers, mode/placement toggles |

### 1.3 Dual Monitoring Problem

**Both the client (`SystemMonitor`) and the backend (`__main__.py`) independently watch battery, charger, and internet status.** This causes:

- Duplicate logic (`check_online()` exists in both `monitor.py` and `backend/__main__.py`)
- Race conditions: backend sends `animation:charging` while client monitor also sets charging
- `backend_override` flag partially mitigates this but is cleared unpredictably when non-looping animations finish

**Recommended fix:** Single source of truth — either client-only monitoring OR backend-only commands, not both.

### 1.4 Animation State Machine

Animations are defined in `utils.py` → `ANIMATIONS` dict. Each entry has:

```python
{"row": int, "frames": int, "speed": int, "loop": bool, "next": str}  # next is optional
```

**Implemented auto-triggers (client `handle_system_metrics`):**

| Condition | Animation |
|---|---|
| Wi‑Fi disconnected | `wifi_disconnected` |
| CPU > 75% | `running` |
| Battery < 20%, unplugged | `need_charging` |
| Charging, battery ≤ 85% | `charging` |
| Charging, battery > 85% | `idle_charged` |
| Charging, battery = 100% | `charged_filled` |
| Unplugged, battery = 100% | `charged_disconnected` |
| Hour 22:00–05:59, mode=idle | `sleeping` |
| Hour 22:00–05:59, mode=wander | `very_tired` |

**Implemented auto-triggers (backend daemon):**

| Event | Animation / Mode |
|---|---|
| Startup | `welcoming` |
| Internet restored | `wifi_connected` → restore state |
| Internet lost | `wifi_disconnected` |
| Charger connected | `charging` / `idle_charged` / `charged_filled` |
| Charger disconnected | `charged_disconnected` / `need_charging` / `mode:wander` |
| Battery hits 100% | `charged_filled` |
| Battery drops below 20% | `need_charging` |
| Battery crosses 85% | `idle_charged` |

**Defined but NOT auto-triggered:**

| Animation | Documented Trigger | Status |
|---|---|---|
| `review` | Task completed, verification ready | ❌ Never triggered |
| `waiting` | AI inference / task loading | ⚠️ Only used randomly during float-wander |
| `failed` | Process failure, syntax error | ⚠️ Manual context menu only |
| `muted` | Sound turned off | ❌ No audio monitoring |
| `unmuted` | Sound restored | ❌ No audio monitoring |
| `need_to_go_bed` | Bedtime reminder (before sleep) | ❌ Night logic skips directly to `very_tired`/`sleeping` |
| `wave` | Greeting / petting | ⚠️ Manual context menu only |

### 1.5 Known Code Issues

| Issue | Location | Severity |
|---|---|---|
| `mouseMouseMoveEvent` — dead stub, typo name | `pet_widget.py:329` | Low |
| `import datetime` inside hot path | `pet_widget.py:178` | Low |
| `backend_override` cleared on any non-looping animation end | `pet_widget.py:131` | Medium |
| Spritesheet `newimage.webp` not in repo | `assets/robot/` | **High** — app won't start without it |
| `temp_rows/` preview images referenced in docs but missing | `assets/robot/` | Medium |
| RAM metric collected, never used | `monitor.py` | Low |
| Bluetooth collected, never used | `monitor.py` | Low |
| "Pet (Beep!)" menu item — no sound playback | `pet_widget.py:409` | Medium |
| Primary monitor only — no multi-monitor support | `pet_widget.py` | Medium |
| Windows-only Wi‑Fi (`netsh`) and Bluetooth (`PowerShell`) | `monitor.py` | Medium |

---

## 2. Documentation Gaps & Fixes

### 2.1 Files That Need Updating

| File | Problem | Required Fix |
|---|---|---|
| **`actions.md`** | Only lists 9 of 22 animations | Add rows 9–21 (charging, wifi, sleep, etc.) |
| **`actions.md`** | Says `idle` has **1 frame** | Correct to **6 frames** (matches `utils.py`) |
| **`actions.md`** | References `spritesheet.webp` | Update to `newimage.webp` (per `pet.json`) |
| **`actions.md`** | Missing behavior modes docs for placement/gravity | Document "Float Freely" vs "Constrain to Taskbar" |
| **`actions.md`** | Missing `SystemMonitor` auto-reaction table | Add client-side trigger conditions |
| **`README.md`** | Sleep window says "10 PM to 6 AM" in animation table | Code uses **22:00–06:00** — align docs |
| **`README.md`** | Folder structure lists `temp_rows/`, `newimage.webp` | Mark as optional / not shipped in repo |
| **`README.md`** | No troubleshooting section | Add port conflict, missing spritesheet, firewall |
| **`README.md`** | No architecture diagram | Add client/backend/process diagram |
| **`new_animations_mapping.md`** | Image previews broken (files not in repo) | Add note: "previews require local `temp_rows/` assets" |
| **All docs** | No API reference for all TCP commands | See [Section 4](#4-tcp-api-expansion) |
| **All docs** | No config reference | Document hardcoded values (port, scale, thresholds) |

### 2.2 New Documentation Files to Create

| File | Purpose |
|---|---|
| **`ARCHITECTURE.md`** | Process model, thread diagram, state machine, event priority rules |
| **`CONFIG.md`** | All tunable constants: port, scale, CPU threshold, battery thresholds, poll intervals |
| **`CONTRIBUTING.md`** | Dev setup, how to add a new animation row, testing checklist |
| **`CHANGELOG.md`** | Version history |

### 2.3 Recommended README Additions

```markdown
## Configuration (Hardcoded — planned: config file)

| Setting | Default | Location |
|---|---|---|
| TCP port | 5050 | `listener.py`, `stub.py` |
| Sprite scale | 0.7 | `client/__main__.py` |
| CPU alert threshold | 75% | `pet_widget.py` |
| Battery low threshold | 20% | `pet_widget.py`, `backend/__main__.py` |
| Battery charged threshold | 85% | `pet_widget.py`, `backend/__main__.py` |
| System poll interval (client) | 3.0 s | `monitor.py` |
| System poll interval (backend) | 1.5 s | `backend/__main__.py` |
| Night mode hours | 22:00–06:00 | `pet_widget.py` |

## Troubleshooting

- **"Spritesheet not found"** — Place `newimage.webp` in `assets/robot/` or update `pet.json`.
- **"Connection refused" on port 5050** — Start the client before the backend.
- **Pet doesn't react to charger** — Both client and backend monitor events; check console logs.
```

---

## 3. Functions That Need to Be Added

### 3.1 High Priority — Core Missing Features

#### A. Audio System Monitor → `muted` / `unmuted`

**Why:** Animations exist, context menu can trigger them, but no system integration.

**Functions to add:**

```python
# src/vision_pet/client/monitor.py

def get_system_volume_muted() -> bool:
    """Return True if Windows master volume is muted."""
    ...

def get_system_volume_level() -> int:
    """Return master volume 0–100."""
    ...
```

**Trigger logic (in `handle_system_metrics`):**
- Volume muted → `set_animation("muted")`
- Volume unmuted (transition) → `set_animation("unmuted")`

**Platform:** Windows via `pycaw` or PowerShell `(New-Object -ComObject WScript.Shell).SendKeys([char]173)` alternative: `nircmd` / Core Audio API.

---

#### B. Inactivity Timer → `very_tired` → `need_rest` → `sleeping`

**Why:** Docs describe inactivity-based tiredness; only clock-based night mode exists.

**Functions to add:**

```python
# src/vision_pet/client/pet_widget.py

def reset_inactivity_timer(self):
    """Call on mouse drag, click, context menu, or backend command."""

def check_inactivity(self):
    """Called from physics loop. Thresholds: 5 min → very_tired, 10 min → need_rest, 15 min → sleeping."""
    ...
```

**Constants:**
```python
INACTIVITY_VERY_TIRED_S = 300   # 5 minutes
INACTIVITY_NEED_REST_S = 600    # 10 minutes
INACTIVITY_SLEEPING_S = 900     # 15 minutes
```

---

#### C. Bedtime Reminder Flow → `need_to_go_bed`

**Why:** Animation row 20 exists but night logic jumps to `very_tired`/`sleeping`.

**Function to add:**

```python
# src/vision_pet/client/pet_widget.py

def check_bedtime_schedule(self) -> str | None:
    """
    Returns animation name or None.
    21:30 → need_to_go_bed (one-shot, transitions to sleeping)
    22:00 → sleeping (if not already)
    06:00 → welcoming (on wake transition)
    """
    ...
```

---

#### D. AI Assistant Integration Hooks → `waiting` / `review` / `failed`

**Why:** These animations map to AI workflow states but have no backend trigger convention.

**Functions to add:**

```python
# src/vision_pet/backend/stub.py

def notify_task_started():
    """Send animation:waiting — AI is processing."""
    return send_command("animation:waiting")

def notify_task_completed():
    """Send animation:review — task succeeded."""
    return send_command("animation:review")

def notify_task_failed():
    """Send animation:failed — task errored."""
    return send_command("animation:failed")
```

**Also add to TCP handler:** support `state:busy`, `state:idle`, `state:error` as semantic aliases.

---

#### E. Pet Sound on Interaction

**Why:** Context menu says "Pet (Beep!)" but triggers `wave` with no audio.

**Functions to add:**

```python
# src/vision_pet/client/audio.py  (new module)

def play_pet_sound(sound_id: str = "beep") -> None:
    """Play a short WAV/OGG from assets/sounds/. Uses QSoundEffect or winsound."""
    ...

def load_sound_config() -> dict:
    """Load sound mappings from assets/sounds/sounds.json."""
    ...
```

**Assets needed:** `assets/sounds/beep.wav`, `assets/sounds/sleep.wav`, etc.

---

#### F. Configuration Module

**Why:** Port, thresholds, scale, and intervals are hardcoded across 5 files.

**Functions to add:**

```python
# src/vision_pet/config.py  (new module)

from dataclasses import dataclass

@dataclass
class VisionConfig:
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 5050
    scale_factor: float = 0.7
    cpu_threshold: float = 75.0
    battery_low_threshold: int = 20
    battery_charged_threshold: int = 85
    client_poll_interval: float = 3.0
    backend_poll_interval: float = 1.5
    night_start_hour: int = 22
    night_end_hour: int = 6
    bedtime_reminder_hour: int = 21
    bedtime_reminder_minute: int = 30
    gravity_enabled_default: bool = False

def load_config(path: str | None = None) -> VisionConfig:
    """Load from vision.toml or vision.json; fall back to defaults."""
    ...
```

**Config file example (`vision.toml`):**
```toml
[tcp]
host = "127.0.0.1"
port = 5050

[display]
scale_factor = 0.7

[thresholds]
cpu_percent = 75
battery_low = 20
battery_charged = 85

[schedule]
night_start = "22:00"
night_end = "06:00"
bedtime_reminder = "21:30"
```

---

### 3.2 Medium Priority — API & UX Enhancements

#### G. Extended TCP Commands

See [Section 4](#4-tcp-api-expansion) for full spec. Key functions:

```python
# src/vision_pet/client/pet_widget.py — extend handle_backend_command

def handle_position_command(self, val: str):
    """Parse position:center|bottom|x,y"""

def handle_gravity_command(self, val: str):
    """Parse gravity:on|off"""

def handle_override_command(self, val: str):
    """Parse override:clear|lock — control backend_override flag"""

def handle_say_command(self, val: str):
    """Parse say:Hello! — show speech bubble (requires new UI widget)"""
```

---

#### H. Speech Bubble Widget

**Why:** Desktop pets typically show short messages from the AI assistant.

**Class to add:**

```python
# src/vision_pet/client/speech_bubble.py

class SpeechBubble(QLabel):
    """Floating text bubble above the pet. Auto-dismiss after timeout."""
    def show_message(self, text: str, duration_ms: int = 4000): ...
    def dismiss(self): ...
```

---

#### I. RAM Usage Reaction

**Why:** RAM is collected but ignored.

**Logic to add in `handle_system_metrics`:**
```python
elif metrics["ram"] > 90.0:
    self.set_animation("running")  # or new "overloaded" animation if added later
```

---

#### J. Multi-Monitor Support

**Functions to add:**

```python
# src/vision_pet/client/pet_widget.py

def get_current_screen(self) -> QScreen:
    """Return the screen the pet is currently on."""

def constrain_to_screen(self, screen: QScreen):
    """Clamp x_pos/y_pos to given screen's availableGeometry."""
```

Update `mouseMoveEvent` and `update_physics_loop` to use `screenAt(QPoint)` instead of `primaryScreen()`.

---

#### K. Consolidate Event Monitoring

**Refactor plan:**

1. Remove duplicate monitoring from backend OR client (recommend: keep client `SystemMonitor`, simplify backend to AI-command relay only)
2. Extract shared utilities:

```python
# src/vision_pet/shared/network.py
def check_online() -> bool: ...

# src/vision_pet/shared/battery.py
def get_battery_state() -> tuple[int, bool]: ...  # (percent, is_charging)
```

---

### 3.3 Low Priority — Platform & Ecosystem

#### L. MCP Server Integration

**Why:** Repo folder is named `MCP` but no Model Context Protocol server exists.

**Proposed module:** `src/vision_pet/mcp_server/`

**MCP tools to expose:**

| Tool | Description |
|---|---|
| `pet_set_animation` | Set animation by name |
| `pet_set_mode` | Set wander/idle mode |
| `pet_say` | Show speech bubble |
| `pet_get_status` | Return current animation, mode, metrics |
| `pet_notify_task_start` | Set waiting animation |
| `pet_notify_task_complete` | Set review animation |
| `pet_notify_task_error` | Set failed animation |

**Dependencies:** `mcp` Python SDK

---

#### M. Cross-Platform System Monitor

| Feature | Windows (current) | Linux (needed) | macOS (needed) |
|---|---|---|---|
| Wi‑Fi status | `netsh wlan` | `nmcli` / `iwgetid` | `networksetup` |
| Bluetooth | PowerShell PnP | `bluetoothctl` | `system_profiler` |
| Volume mute | pycaw / COM | `pactl` | `osascript` |

**Function to add:**

```python
# src/vision_pet/client/platform/__init__.py

def get_platform_monitor() -> "PlatformMonitor":
    """Factory returning WindowsMonitor, LinuxMonitor, or MacOSMonitor."""
    ...
```

---

#### N. Persistence (Save Position & Preferences)

```python
# src/vision_pet/client/settings.py

def save_settings(x, y, mode, gravity_enabled, scale) -> None: ...
def load_settings() -> dict: ...
```

Store in `%APPDATA%/VISION/settings.json` (Windows) or `~/.config/vision/settings.json`.

---

#### O. Logging Framework

Replace `print()` statements with structured logging:

```python
# src/vision_pet/logging_config.py
import logging

def setup_logging(level=logging.INFO, log_file=None): ...
```

---

## 4. TCP API Expansion

### 4.1 Current API (Implemented)

| Command | Format | Example | Response |
|---|---|---|---|
| Set animation | `animation:<name>` | `animation:wave` | `OK` |
| Set mode | `mode:wander\|idle` | `mode:idle` | `OK` |

### 4.2 Proposed API (To Implement)

| Command | Format | Example | Effect |
|---|---|---|---|
| Clear override | `override:clear` | — | Resume system auto-reactions |
| Lock override | `override:lock` | — | Block system auto-reactions until cleared |
| Set gravity | `gravity:on\|off` | `gravity:on` | Toggle taskbar constraint |
| Set position | `position:<preset>` | `position:bottom` | Snap to center/bottom |
| Set position (absolute) | `position:<x>,<y>` | `position:400,300` | Move to coordinates |
| Show message | `say:<text>` | `say:Build complete!` | Speech bubble |
| Semantic state | `state:busy\|idle\|error\|success` | `state:busy` | Maps to waiting/idle/failed/review |
| Get status | `status:query` | — | Returns JSON: animation, mode, metrics |
| Ping | `ping` | — | Returns `PONG` |

### 4.3 Example: Full AI Assistant Integration

```python
from src.vision_pet.backend.stub import send_command

class VisionPetBridge:
    """Wrapper for AI agent workflows."""

    def on_prompt_received(self):
        send_command("state:busy")          # → waiting animation

    def on_response_ready(self):
        send_command("state:success")       # → review animation

    def on_error(self, message: str):
        send_command("state:error")         # → failed animation
        send_command(f"say:{message}")      # → speech bubble

    def on_idle(self):
        send_command("override:clear")
        send_command("mode:wander")
```

---

## 5. Code Quality & Infrastructure

### 5.1 Testing (None Exist Today)

| Test File | What to Cover |
|---|---|
| `tests/test_utils.py` | `load_animations`, `pil_to_pixmap`, frame counts |
| `tests/test_listener.py` | TCP bind, command parsing, `OK` response |
| `tests/test_stub.py` | `send_command` with mock socket |
| `tests/test_config.py` | Config load defaults and overrides |
| `tests/test_state_machine.py` | Animation `next` transitions |

**Framework:** `pytest` + `pytest-qt` for widget tests

### 5.2 Packaging

Add `pyproject.toml`:

```toml
[project]
name = "vision-pet"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["PySide6>=6.0.0", "pillow>=10.0.0", "psutil>=5.9.0"]

[project.scripts]
vision-pet = "vision_pet.client.__main__:main"
vision-backend = "vision_pet.backend.__main__:main"
```

### 5.3 CI Pipeline (`.github/workflows/ci.yml`)

- `ruff check` — linting
- `pytest` — unit tests
- Verify `pet.json` schema
- Optional: smoke test with headless Qt (`QT_QPA_PLATFORM=offscreen`)

### 5.4 Code Cleanup Tasks

| Task | File |
|---|---|
| Remove dead `mouseMouseMoveEvent` | `pet_widget.py:329` |
| Move `import datetime` to top | `pet_widget.py` |
| Deduplicate `check_online()` | Extract to `shared/network.py` |
| Validate animation names in TCP handler against `ANIMATIONS` keys | `pet_widget.py` |
| Add type hints to public functions | All modules |

---

## 6. Implementation Priority Matrix

| Priority | Item | Effort | Impact |
|:---:|---|:---:|:---:|
| 🔴 P0 | Add spritesheet asset or fallback placeholder | Small | **Blocks startup** |
| 🔴 P0 | Fix documentation inconsistencies (`actions.md`, README sleep hours) | Small | High |
| 🔴 P0 | Add `config.py` + `vision.toml` | Medium | High |
| 🟠 P1 | Consolidate duplicate monitoring (client vs backend) | Medium | High |
| 🟠 P1 | AI hooks: `waiting` / `review` / `failed` semantic states | Small | High |
| 🟠 P1 | Inactivity timer → tired/sleep chain | Medium | High |
| 🟠 P1 | Audio: pet beep + mute/unmute detection | Medium | Medium |
| 🟡 P2 | Extended TCP API (override, position, say, status) | Medium | High |
| 🟡 P2 | Speech bubble widget | Medium | Medium |
| 🟡 P2 | Bedtime reminder (`need_to_go_bed`) | Small | Medium |
| 🟡 P2 | Settings persistence (save position) | Small | Medium |
| 🟢 P3 | MCP server module | Large | Medium |
| 🟢 P3 | Multi-monitor support | Medium | Medium |
| 🟢 P3 | Cross-platform monitors (Linux/macOS) | Large | Medium |
| 🟢 P3 | Unit tests + CI | Medium | High (long-term) |
| 🟢 P3 | `pyproject.toml` packaging | Small | Medium |

---

## Quick Reference: Module Map (Current)

```
src/vision_pet/
├── __init__.py
├── client/
│   ├── __main__.py      → Entry: load spritesheet, create DesktopPet
│   ├── pet_widget.py    → DesktopPet: animation, physics, menu, TCP handler
│   ├── listener.py      → BackendListener: TCP server thread
│   ├── monitor.py       → SystemMonitor: CPU/RAM/battery/Wi‑Fi/BT thread
│   └── utils.py         → ANIMATIONS dict, load_animations(), pil_to_pixmap()
└── backend/
    ├── __main__.py      → Event polling daemon loop
    └── stub.py          → send_command() TCP client helper
```

## Quick Reference: Proposed Module Map

```
src/vision_pet/
├── config.py            → VisionConfig, load_config()
├── logging_config.py    → setup_logging()
├── shared/
│   ├── network.py       → check_online()
│   └── battery.py       → get_battery_state()
├── client/
│   ├── audio.py         → play_pet_sound()
│   ├── speech_bubble.py → SpeechBubble widget
│   ├── settings.py      → save/load user preferences
│   └── platform/
│       ├── windows.py
│       ├── linux.py
│       └── darwin.py
├── backend/
│   └── bridge.py        → VisionPetBridge AI workflow wrapper
└── mcp_server/
    └── server.py        → MCP tool definitions
```

---

*This document should be updated as features are implemented. Mark items with ✅ when complete.*
