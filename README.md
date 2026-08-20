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
- 🔌 **TCP API Listener**: Runs a local TCP server on port `5050` to receive animation and mode overrides from the backend.
- 📈 **Stateful Event Monitor (Backend)**: Runs a background system daemon that checks charger connection status, battery levels, and internet connectivity, sending priority-based warning animations to the client.
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
│       ├── client/         # Desktop Pet client subpackage
│       │   ├── __init__.py
│       │   ├── __main__.py # Client runner (resolves pet.json path and scaling)
│       │   ├── listener.py # TCP socket server thread
│       │   ├── pet_widget.py # PySide6 window widget, physics loop & context menu
│       │   └── utils.py    # Image slicing, conversion, and row configurations
│       └── backend/        # Custom backend/integration subpackage
│           ├── __init__.py
│           ├── __main__.py # Live system event monitor daemon loop
│           └── stub.py     # Socket communication helper
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

---

## Running VISION

### Run Client & Event Monitor Daemon Together
To launch both the desktop pet companion and the live event-monitoring backend daemon concurrently:
```bash
python main.py
```
This starts the pet widget (greeting you with a wave), binds the port `5050`, and then launches the backend monitor loop. 

Try plugging/unplugging your laptop charger or disconnecting your network—the pet will immediately react on your screen!

### Run Individually
If you want to run the components separately:

1. **Launch the pet companion client:**
   ```bash
   python -m src.vision_pet.client
   ```
2. **Run the backend monitor daemon in a separate terminal:**
   ```bash
   python -m src.vision_pet.backend
   ```

---

## Backend Integration API

VISION runs a background socket listener so your main Python backend or agent can easily change the pet's display states dynamically.

### Communication Protocol
Send a simple UTF-8 encoded TCP string to `127.0.0.1:5050` in the format `command:value`:

| Command | Possible Values | Effect |
|---|---|---|
| `animation` | Any animation key (see table below) | Switches the active animation cycle |
| `mode` | `wander`, `idle` | Changes movement behavior (autopilot wandering or stationary) |

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
| **9** | `charging` | 6 | 140 | True | `idle_charged` | Plugged in and actively drawing power. |
| **10** | `charged_disconnected` | 5 | 200 | True | `idle` | Battery full, cable unplugged, content state. |
| **11** | `charged_filled` | 6 | 130 | False | `charged_disconnected` | One-shot fill-up animation when charge completes. |
| **12** | `need_charging` | 6 | 160 | True | `charging` | Low battery warning (< 20%), prompts user to plug in. |
| **13** | `wifi_connected` | 5 | 150 | False | `idle` | Signal-acquired confirmation after reconnect. |
| **14** | `wifi_disconnected` | 5 | 180 | True | -- | Connection lost / offline state indicator. |
| **15** | `muted` | 5 | 200 | True | -- | Sound turned off, persists until unmuted. |
| **16** | `unmuted` | 5 | 150 | False | `idle` | Sound restored confirmation. |
| **17** | `very_tired` | 6 | 220 | True | `need_rest` | Extended inactivity or low-energy state. |
| **18** | `need_rest` | 6 | 220 | True | `sleeping` | Prompts user that pet wants to sleep soon. |
| **19** | `sleeping` | 6 | 260 | True | -- | Idle-timeout or scheduled sleep state (10 PM to 6 AM). |
| **20** | `need_to_go_bed` | 5 | 200 | False | `sleeping` | Bedtime reminder before transitioning to sleep. |
| **21** | `welcoming` | 6 | 130 | False | `idle` | App-open or user-return greeting. |
