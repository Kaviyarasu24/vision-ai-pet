# VISION — AI Desktop Pet Companion

**VISION** is an interactive AI desktop pet designed as a visual companion for a personal AI assistant. It floats on top of your screen as a borderless overlay, reacting to drag-and-drop actions, gravity, and system commands in real time.

VISION features expressive animations, system awareness, and integration capabilities with your custom Python backend.

---

## Features

- 🖥️ **Transparent Desktop Widget**: Frameless, transparent, and always-on-top window overlay.
- 🎨 **Slick Spritesheet Rendering**: Slices and displays high-clarity pixel-art frames from `spritesheet.webp` in real-time.
- 🧲 **Mouse Physics & Dragging**: Click and drag the pet anywhere on your desktop; release it to let it fall with gravity.
- 🌍 **Screen Awareness**: Restricts movement within your active desktop boundaries and snaps to the top of your Windows taskbar.
- 🤖 **Autopilot Wander**: Walks, runs, and hops autonomously when not being dragged or directed.
- 🔌 **TCP API Listener**: Runs a local TCP server on port `5050` to receive instant animation and mode overrides from your custom Python backend.
- 🛠️ **Desktop Control**: Right-click on the pet to open a context menu to manually trigger animations or close the application.

---

## Folder Structure

```text
vision-ai-pet/
├── assets/                 # Central assets folder
│   └── robot/
│       ├── pet.json         # Pet metadata (casing details, names, description)
│       └── spritesheet.webp # Sprite assets (8x9 Grid of 192x208px animation frames)
├── src/                    # Source package directory
│   └── vision_pet/
│       ├── __init__.py
│       ├── client/         # Desktop Pet client subpackage
│       │   ├── __init__.py
│       │   ├── __main__.py # Client runner entry point
│       │   ├── listener.py # TCP socket server thread
│       │   ├── pet_widget.py # PySide6 window widget & physics loop
│       │   └── utils.py    # Image loader and conversion utilities
│       └── backend/        # Custom backend/integration subpackage
│           ├── __init__.py
│           ├── __main__.py # Backend integration test loop runner
│           └── stub.py     # Socket communication helper
├── requirements.txt        # List of package dependencies
└── README.md               # Project documentation (this file)
```

---

## Installation

1. Make sure you have **Python 3.12+** installed on your system.
2. Install the required GUI and image handling dependencies:
   ```bash
   pip install PySide6 pillow
   ```

---

## Running VISION

To launch the desktop pet companion client on your screen:
```bash
python -m src.vision_pet.client
```
This runs the PySide6 pet client and starts listening for socket commands on `127.0.0.1:5050`.

To run the sample backend integration loop in a separate terminal:
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
| `animation` | `idle`, `running_right`, `running_left`, `wave`, `jump`, `failed`, `waiting`, `running`, `review` | Switches the active animation cycle |
| `mode` | `wander`, `idle` | Changes movement behavior (autopilot wandering or stationary) |

### Python Integration Example
Here is how your backend can trigger animations:

```python
import socket

def set_pet_state(command: str):
    """
    Sends a state-change instruction to the running VISION desktop pet.
    Example commands: "animation:wave", "mode:idle", "animation:review"
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("127.0.0.1", 5050))
            s.sendall(command.encode('utf-8'))
            response = s.recv(1024).decode('utf-8')
            return response
    except ConnectionRefusedError:
        return "Companion is not running"

# Example: Make the pet wave
set_pet_state("animation:wave")
```

---

## Animation States (`spritesheet.webp`)

The spritesheet contains **8 columns** and **9 rows** (each frame is **192x208px**). Slicing mapping used by `desktop_pet.py`:

| Row (0-indexed) | Animation Name | Frame Count | Recommended Use Cases |
|:---:|---|:---:|---|
| **0** | `idle` | 6 | Standby state, blinking screens |
| **1** | `running_right` | 8 | Wandering to the right of the screen |
| **2** | `running_left` | 8 | Wandering to the left of the screen |
| **3** | `wave` | 4 | Welcoming, greeting, or petting gratitude |
| **4** | `jump` | 5 | Hop animation or lifting action |
| **5** | `failed` | 8 | Backend process failure or error warnings |
| **6** | `waiting` | 6 | Task compiles, model inference, or database loads |
| **7** | `running` | 6 | Code execution or general computations |
| **8** | `review` | 6 | Compilation success, review ready, or task finished |
