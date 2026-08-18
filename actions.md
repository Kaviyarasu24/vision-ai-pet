# VISION — AI Desktop Pet Actions

This document lists all the interactive animations, autopilot behaviors, and API commands supported by the VISION Desktop Pet.

---

## 🎭 Animation States

These animations are sliced from `spritesheet.webp` and represent the visual states of the companion:

| Animation Name | Row (0-indexed) | Frames | Typical Use Cases |
| :--- | :---: | :---: | :--- |
| `idle` | **0** | 1 | Stationary standby state (single stable frame). |
| `running_right` | **1** | 8 | Wandering to the right of the screen. |
| `running_left` | **2** | 8 | Wandering to the left of the screen. |
| `wave` | **3** | 4 | Greeting, welcome prompt, or petting reaction. |
| `jump` | **4** | 5 | Lifting action or jumping up during wander. |
| `failed` | **5** | 8 | Process failure, syntax error, or warnings. |
| `waiting` | **6** | 6 | Model inference, task loading, or database compile. |
| `running` | **7** | 6 | Active code execution or computations. |
| `review` | **8** | 6 | Process success, verification ready, or tasks completed. |

---

## 🎯 Behavior Modes

The pet runs in one of two autonomy modes:

* **Autopilot Wander (`wander`):**
  The pet autonomously wanders across the screen, snaps to boundaries, walks left/right, and hops randomly.
* **Static Idle (`idle`):**
  The pet remains completely stationary at its current coordinates.

---

## 🔌 Socket Control API

You can trigger these animations and modes dynamically from your custom Python backend by sending a UTF-8 socket message to `127.0.0.1:5050` in the format `command:value`:

### 1. Trigger Animation
Send `animation:<name>` (e.g. `animation:wave`):
```python
import socket

def set_animation(name):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 5050))
        s.sendall(f"animation:{name}".encode())
        return s.recv(1024).decode()
```

### 2. Trigger Behavior Mode
Send `mode:<name>` (e.g. `mode:idle`):
```python
import socket

def set_mode(mode_name):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 5050))
        s.sendall(f"mode:{mode_name}".encode())
        return s.recv(1024).decode()
```
