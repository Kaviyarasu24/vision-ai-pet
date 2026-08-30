# VISION — AI Desktop Pet Companion

**VISION** is an interactive AI desktop pet designed as a visual companion for a personal AI assistant. It floats on top of your screen as a borderless overlay, reacting to drag-and-drop actions, gravity, and system commands in real time.

VISION features expressive animations, system awareness, and priority-guarded integration capabilities with your custom Python backend.

---

## Features

- 🖥️ **Transparent Desktop Widget**: Frameless, transparent, and always-on-top window overlay.
- 🎨 **Dynamic Spritesheet Rendering**: Slices and displays pixel-art frames in real-time. Spritesheet configuration is dynamically resolved via `pet.json`.
- 🔍 **Perfect Quality Scaling**: Sized adaptively (scaled to 70% bounds by default) using nearest-neighbor scaling to preserve clean pixel outlines.
- 🧲 **Mouse Physics & Dragging**: Click and drag the pet anywhere on your desktop; release it to let it fall with gravity.
- 🌍 **Screen Awareness**: Restricts movement within your active desktop boundaries and snaps to the top of your Windows taskbar.
- 🤖 **Autopilot Wander**: Walks, runs, and hops autonomously when not being dragged or directed.
- 💬 **Speech Bubble**: The AI can push short messages (`say:<text>`) that float above the pet and auto-dismiss.
- 🖥️➡️🖥️ **Multi-Monitor Aware**: Tracks whichever display the pet sits on; drag it across monitors and it re-adopts the new screen's work area.
- 🔌 **TCP API Listener**: Runs a local TCP server on port `5050` to receive animation, mode, AI-state, and override commands from a backend.
- 📈 **Single-Process System Awareness**: One background thread watches CPU, RAM, battery, charger, Wi‑Fi (and, optionally, audio mute) and reacts to both steady-state conditions and transition events (charger plug/unplug, reconnect, battery thresholds) — no separate daemon, no race conditions.
- 🛠️ **Desktop Control Menu**: Right-click on the pet to open a context menu to inspect system metrics, manually trigger animations, or close the companion.

---

## Folder Structure

```text
vision-ai-pet/
├── assets/                 # Central assets folder
│   └── robot/
│       ├── pet.json         # Pet metadata (active spritesheetPath, displayName)
│       ├── newimage.webp    # Crisp, high-contrast 22-row spritesheet
│       └── temp_rows/       # Individual frame samples for visual guide reference
├── src/                    # Source package directory
│   └── vision_pet/
│       ├── __init__.py
│       ├── client/         # Desktop Pet client subpackage (single source of truth)
│       │   ├── __init__.py
│       │   ├── __main__.py # Client runner (resolves pet.json path and scaling)
│       │   ├── listener.py # TCP socket server thread
│       │   ├── monitor.py  # System monitor thread (CPU/RAM/battery/Wi‑Fi/BT/mute)
│       │   ├── pet_widget.py # PySide6 widget: animation, physics, reactions, menu
│       │   └── utils.py    # Image slicing, conversion, and row configurations
│       └── backend/        # Optional AI-relay / legacy daemon subpackage
│           ├── __init__.py
│           ├── __main__.py # Legacy standalone event daemon (not auto-launched)
│           └── stub.py     # send_command() + AI notify_* helpers
├── requirements.txt        # List of package dependencies
├── new_animations_mapping.md # Visual guide previewing all 22 animation rows
└── README.md               # Project documentation (this file)
```

---

## Installation

1. Make sure you have **Python 3.12+** installed on your system.
2. Install the required GUI, system monitoring, and image handling dependencies:
   ```bash
   pip install PySide6 pillow psutil
   ```
3. *(Optional)* For audio mute/unmute reactions, also install:
   ```bash
   pip install pycaw comtypes
   ```
   Without these, the app runs normally and simply skips the `muted`/`unmuted`
   animations.

---

## Running VISION

### Launch the companion
```bash
python main.py
```
This starts the pet widget (greeting you with a wave), binds port `5050`, and
begins monitoring your system in a single background thread. Try plugging/
unplugging your charger or disconnecting your network — the pet reacts on screen.

You can also run the client module directly:
```bash
python -m src.vision_pet.client
```

> **Note:** As of the monitoring consolidation, `main.py` runs a **single
> process**. The client itself is the source of truth for all system reactions.
> The old always-on backend polling daemon (`python -m src.vision_pet.backend`)
> is now **optional/legacy** — it duplicated this monitoring in a second
> interpreter and competed with the client for control of the pet.

### Optional: AI assistant integration
The `backend` package doubles as a relay for external AI workflows. From your
agent code:
```python
from src.vision_pet.backend.stub import (
    notify_task_started, notify_task_completed, notify_task_failed, notify_idle,
)

notify_task_started()    # pet shows the looping "waiting" animation
notify_task_completed()  # one-shot "review", then resumes automatic behavior
notify_task_failed()     # one-shot "failed", then resumes
notify_idle()            # release the hold, back to system-driven reactions

from src.vision_pet.backend.stub import say
say("Deploying to prod…")  # short message bubble floats above the pet
```

---

## Backend Integration API

VISION runs a background socket listener so your main Python backend or agent can
change the pet's display states dynamically.

### Communication Protocol
Send a UTF-8 encoded TCP string to `127.0.0.1:5050` in the format `command:value`:

| Command | Possible Values | Effect |
|---|---|---|
| `animation` | Any animation key (see table below) | Switches the active animation cycle (locks the override) |
| `mode` | `wander`, `idle` | Changes movement behavior; clears the override |
| `state` | `busy`, `success`, `error`, `idle` | Semantic AI states → `waiting` / `review` / `failed` / release |
| `override` | `clear`, `lock` | Resume (or block) automatic system reactions |
| `say` | any short text | Show a floating speech bubble above the pet (auto-dismisses; original case preserved) |

---

## Animation Mappings (`newimage.webp`)

The spritesheet is configured via the `ANIMATIONS` dictionary in [`utils.py`](file:///d:/MCP/src/vision_pet/client/utils.py#L11). Mappings used by the client:

| Row (0-indexed) | Animation Name | Frames | Speed (ms) | Loop | Next State | Description / Trigger Case |
|:---:|---|:---:|:---:|:---:|:---:|---|
| **0** | `idle` | 6 | 150 | True | -- | Standard blinking screen standby state. |
| **1** | `running_right` | 8 | 100 | True | -- | Wandering towards the right. |
| **2** | `running_left` | 8 | 100 | True | -- | Wandering towards the left. |
| **3** | `wave` | 4 | 180 | False | `idle` | Greet or petting reaction wave. |
| **4** | `jump` | 5 | 120 | False | `idle` | Hopping action or cursor drag reaction. |
| **5** | `failed` | 8 | 150 | False | `idle` | Error or unsuccessful action reaction. |
| **6** | `waiting` | 6 | 180 | True | -- | Idle, awaiting input or response pending. |
| **7** | `running` | 6 | 100 | True | -- | General/alt movement loop. |
| **8** | `review` | 6 | 200 | False | `idle` | Thinking/reviewing pose after an action. |
| **9** | `charging` | 6 | 140 | True | `idle_charged` | Plugged in and actively drawing power (loops while battery <= 85%). |
| **10** | `charged_disconnected` | 5 | 200 | True | `idle` | Cable unplugged content state, or plugged-in standby state (when battery > 85%). |
| **11** | `charged_filled` | 6 | 130 | False | `charged_disconnected` | One-shot fill-up animation when charge completes. |
| **12** | `need_charging` | 6 | 160 | True | `charging` | Low battery warning (< 20%), prompts user to plug in. |
| **13** | `wifi_connected` | 5 | 150 | False | `idle` | Signal-acquired confirmation after reconnect. |
| **14** | `wifi_disconnected` | 5 | 180 | True | -- | Connection lost / offline state indicator. |
| **15** | `muted` | 5 | 200 | True | -- | Sound turned off, persists until unmuted. |
| **16** | `unmuted` | 5 | 150 | False | `idle` | Sound restored confirmation. |
| **17** | `very_tired` | 6 | 220 | False | `need_rest` | Extended inactivity or low-energy state. |
| **18** | `need_rest` | 6 | 220 | False | `sleeping` | Prompts user that pet wants to sleep soon. |
| **19** | `sleeping` | 6 | 260 | True | -- | Idle-timeout or scheduled sleep state (10 PM to 6 AM). |
| **20** | `need_to_go_bed` | 5 | 200 | False | `sleeping` | Bedtime reminder before transitioning to sleep. |
| **21** | `welcoming` | 6 | 130 | False | `idle` | App-open or user-return greeting. |

---

## Automatic Reactions (client-driven)

The client monitors the system every ~3 s and reacts by priority. Transition
events fire one-shot confirmations; everything else is steady-state.

| Condition | Animation |
|---|---|
| Internet just restored | `wifi_connected` (one-shot) |
| Battery just reached 100% while plugged | `charged_filled` (one-shot) |
| Volume mute toggled *(needs pycaw)* | `muted` / `unmuted` |
| Network down | `wifi_disconnected` |
| CPU > 75% or RAM > 90% | `running` |
| Battery < 20% and unplugged | `need_charging` |
| Charging, ≤ 85% / > 85% | `charging` / `idle_charged` |
| Unplugged and full | `charged_disconnected` |
| Nightfall (22:00) | `need_to_go_bed` → `sleeping` |
| 5 min of inactivity (daytime) | `very_tired` → `need_rest` → `sleeping` |

---

## Configuration Reference (hardcoded)

| Setting | Default | Location |
|---|---|---|
| TCP host / port | `127.0.0.1:5050` | `listener.py`, `stub.py` |
| Sprite scale | `0.7` | `client/__main__.py` |
| CPU alert threshold | `75%` | `pet_widget.py` |
| RAM alert threshold | `90%` | `pet_widget.py` |
| Battery low / charged | `20%` / `85%` | `pet_widget.py` |
| Inactivity → sleep | `300 s` | `pet_widget.py` (`INACTIVITY_SLEEP_S`) |
| Night window | `22:00–06:00` | `pet_widget.py` |
| Physics tick (moving / idle) | `16 ms` / `66 ms` | `pet_widget.py` |
| Monitor poll interval | `3.0 s` | `monitor.py` |

---

## Troubleshooting

- **"Spritesheet not found"** — ensure the file named by `pet.json`
  (`newimage.webp` by default) exists in `assets/robot/`.
- **"Connection refused" on port 5050** — start the client before sending TCP
  commands; only one client can bind the port at a time.
- **Pet stuck in one animation** — a backend `animation:`/`state:busy` command
  locks the override. Send `override:clear`, `mode:wander`, or `state:idle` to
  resume automatic reactions.
- **No `muted`/`unmuted` reactions** — install the optional `pycaw` + `comtypes`.
