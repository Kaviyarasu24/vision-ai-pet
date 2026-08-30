# VISION — AI Desktop Pet Actions

This document lists all interactive animations, autopilot behaviors, and API
commands supported by the VISION Desktop Pet.

---

## 🎭 Animation States

Animations are sliced from the spritesheet named in `assets/robot/pet.json`
(`newimage.webp` by default), configured via the `ANIMATIONS` dict in
`client/utils.py`.

| Row | Name | Frames | Loop | Typical Use / Trigger |
| :--: | :--- | :----: | :--: | :--- |
| 0 | `idle` | 6 | ✅ | Standard standby / blink state. |
| 1 | `running_right` | 8 | ✅ | Wandering right. |
| 2 | `running_left` | 8 | ✅ | Wandering left. |
| 3 | `wave` | 4 | ❌ | Greeting / petting reaction. |
| 4 | `jump` | 5 | ❌ | Hop, or reaction to being grabbed. |
| 5 | `failed` | 8 | ❌ | Error (`state:error`) or manual trigger. |
| 6 | `waiting` | 6 | ✅ | AI busy (`state:busy`). |
| 7 | `running` | 6 | ✅ | High CPU (>75%) or RAM (>90%). |
| 8 | `review` | 6 | ❌ | Task success (`state:success`). |
| 9 | `charging` | 6 | ✅ | Plugged in, battery ≤ 85%. |
| 10 | `charged_disconnected` | 5 | ✅ | Full and unplugged. |
| 11 | `charged_filled` | 6 | ❌ | Battery just reached 100% while plugged. |
| 12 | `need_charging` | 6 | ✅ | Battery < 20% and unplugged. |
| 13 | `wifi_connected` | 5 | ❌ | Internet just restored. |
| 14 | `wifi_disconnected` | 5 | ✅ | Network down. |
| 15 | `muted` | 5 | ✅ | Volume muted *(needs pycaw)*. |
| 16 | `unmuted` | 5 | ❌ | Volume restored *(needs pycaw)*. |
| 17 | `very_tired` | 6 | ❌ | Long inactivity / low energy → `need_rest`. |
| 18 | `need_rest` | 6 | ❌ | → `sleeping`. |
| 19 | `sleeping` | 6 | ✅ | Night (22:00–06:00) or 5 min inactivity. |
| 20 | `need_to_go_bed` | 5 | ❌ | Bedtime reminder at nightfall → `sleeping`. |
| 21 | `welcoming` | 6 | ❌ | App open / return greeting. |

---

## 🎯 Behavior & Placement Modes

- **Autopilot Wander (`wander`):** the pet autonomously walks, hops, and snaps
  to boundaries.
- **Static Idle (`idle`):** the pet stays put at its current coordinates.
- **Float Freely:** no gravity; the pet can hover anywhere (default).
- **Constrain to Taskbar:** gravity on; the pet falls and rests on the taskbar.

All four are toggled from the right-click context menu.

---

## 🔌 Socket Control API

Send a UTF-8 message to `127.0.0.1:5050` in the form `command:value`. Each call
returns `OK`.

| Command | Values | Effect |
| :--- | :--- | :--- |
| `animation:<name>` | any animation key above | Play that animation (locks override) |
| `mode:<name>` | `wander`, `idle` | Set movement mode (clears override) |
| `state:<name>` | `busy`, `success`, `error`, `idle` | AI states → `waiting` / `review` / `failed` / release |
| `override:<name>` | `clear`, `lock` | Resume / block automatic system reactions |
| `say:<text>` | any short message | Show a speech bubble above the pet (auto-dismisses ~4 s; case preserved) |

```python
import socket

def send(command):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1", 5050))
        s.sendall(command.encode())
        return s.recv(1024).decode()

send("state:busy")       # pet shows "waiting" while the AI works
send("state:success")    # one-shot "review", then resumes automatic behavior
send("override:clear")   # hand control back to the system monitor
send("say:Deploying to prod…")  # floating message bubble above the pet
```

Convenience helpers live in `src/vision_pet/backend/stub.py`
(`notify_task_started`, `notify_task_completed`, `notify_task_failed`,
`notify_idle`).

> **Note:** The client monitors the system itself in a single background
> thread — there is no separate always-on daemon in the default run path.
