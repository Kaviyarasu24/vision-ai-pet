import sys
import os
import socket
import random
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QMenu
from PySide6.QtCore import Qt, QTimer, QPoint, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QAction
from PIL import Image

# Spritesheet configuration
SPRITE_WIDTH = 192
SPRITE_HEIGHT = 208
COLS = 8
ROWS = 9

ANIMATIONS = {
    "idle": {"row": 0, "frames": 6, "speed": 150, "loop": True},
    "running_right": {"row": 1, "frames": 8, "speed": 100, "loop": True},
    "running_left": {"row": 2, "frames": 8, "speed": 100, "loop": True},
    "wave": {"row": 3, "frames": 4, "speed": 180, "loop": False, "next": "idle"},
    "jump": {"row": 4, "frames": 5, "speed": 120, "loop": False, "next": "idle"},
    "failed": {"row": 5, "frames": 8, "speed": 120, "loop": True},
    "waiting": {"row": 6, "frames": 6, "speed": 150, "loop": True},
    "running": {"row": 7, "frames": 6, "speed": 100, "loop": True},
    "review": {"row": 8, "frames": 6, "speed": 150, "loop": True}
}

def pil_to_pixmap(pil_img):
    """Converts a PIL Image to PySide6 QPixmap preserving alpha transparency."""
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_img.size[0], pil_img.size[1], QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)

def load_animations(sheet_path):
    """Crops spritesheet frames using Pillow and loads them into a dictionary of QPixmaps."""
    if not os.path.exists(sheet_path):
        raise FileNotFoundError(f"Spritesheet not found at: {sheet_path}")
        
    img = Image.open(sheet_path).convert("RGBA")
    anims = {}
    for name, config in ANIMATIONS.items():
        row = config["row"]
        frames_count = config["frames"]
        frames = []
        for col in range(frames_count):
            box = (
                col * SPRITE_WIDTH,
                row * SPRITE_HEIGHT,
                (col + 1) * SPRITE_WIDTH,
                (row + 1) * SPRITE_HEIGHT
            )
            crop_frame = img.crop(box)
            frames.append(pil_to_pixmap(crop_frame))
        anims[name] = frames
    return anims


class BackendListener(QThread):
    """Runs a background TCP socket server to accept commands from the Python backend."""
    command_received = Signal(str)

    def __init__(self, host="127.0.0.1", port=5050):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((self.host, self.port))
            server.listen(5)
            server.settimeout(1.0) # Periodically check running state
        except Exception as e:
            print(f"[Listener] Error binding to {self.host}:{self.port}: {e}")
            return

        print(f"[Listener] Listening for commands on TCP {self.host}:{self.port}...")
        while self.running:
            try:
                conn, addr = server.accept()
            except socket.timeout:
                continue
            except Exception:
                break

            try:
                conn.settimeout(2.0)
                data = conn.recv(1024).decode('utf-8').strip()
                if data:
                    self.command_received.emit(data)
                conn.sendall(b"OK\n")
            except Exception as e:
                print(f"[Listener] Connection error: {e}")
            finally:
                conn.close()

        server.close()

    def stop(self):
        self.running = False
        self.wait()


class DesktopPet(QWidget):
    """The frameless, transparent QWidget desktop pet client."""
    def __init__(self, anims):
        super().__init__()
        self.anims = anims

        # Window styling: frameless, stay on top, hide taskbar entry (Tool window)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # UI Elements
        self.label = QLabel(self)
        self.label.setFixedSize(SPRITE_WIDTH, SPRITE_HEIGHT)
        self.setFixedSize(SPRITE_WIDTH, SPRITE_HEIGHT)

        # Physics & Position States
        self.x_pos = 200
        self.y_pos = 200
        self.vx = 0
        self.vy = 0
        self.gravity = 0.8
        self.is_dragging = False
        self.drag_offset = QPoint()

        # Behavior States
        self.mode = "wander"  # "wander", "idle"
        self.wander_timer = 0
        self.wander_direction = 0  # -1: left, 1: right, 0: idle

        # Animation states
        self.current_anim = "idle"
        self.current_frame = 0
        self.update_sprite_display()

        # Animation frame timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.advance_animation_frame)
        self.anim_timer.start(ANIMATIONS[self.current_anim]["speed"])

        # Physics/Wander update loop (runs at ~60fps)
        self.physics_timer = QTimer(self)
        self.physics_timer.timeout.connect(self.update_physics_loop)
        self.physics_timer.start(16)

        # Context Menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # Initialize socket backend listener
        self.listener = BackendListener()
        self.listener.command_received.connect(self.handle_backend_command)
        self.listener.start()

        # Initial snap to bottom of desktop screen
        self.snap_to_bottom()
        self.show()

    def snap_to_bottom(self):
        """Snaps the pet immediately to the bottom of the screen taskbar work-area."""
        avail_geo = QApplication.primaryScreen().availableGeometry()
        self.x_pos = (avail_geo.width() - SPRITE_WIDTH) // 2 + avail_geo.x()
        self.y_pos = avail_geo.height() - SPRITE_HEIGHT + avail_geo.y()
        self.move(int(self.x_pos), int(self.y_pos))

    def set_animation(self, name):
        """Transition current animation loop to new set."""
        if self.current_anim == name:
            return
        if name in self.anims:
            self.current_anim = name
            self.current_frame = 0
            self.anim_timer.setInterval(ANIMATIONS[self.current_anim]["speed"])
            self.update_sprite_display()

    def advance_animation_frame(self):
        """Advances current animation cycle frame by frame."""
        config = ANIMATIONS[self.current_anim]
        self.current_frame += 1
        if self.current_frame >= len(self.anims[self.current_anim]):
            if config["loop"]:
                self.current_frame = 0
            else:
                next_state = config.get("next", "idle")
                self.set_animation(next_state)
                return
        self.update_sprite_display()

    def update_sprite_display(self):
        """Updates UI label pixmap."""
        pixmap = self.anims[self.current_anim][self.current_frame]
        self.label.setPixmap(pixmap)

    def update_physics_loop(self):
        """Main engine tick running at 60 FPS. Handles gravity, bounds, and wander behaviors."""
        if self.is_dragging:
            return

        avail_geo = QApplication.primaryScreen().availableGeometry()
        min_x = avail_geo.x()
        max_x = avail_geo.x() + avail_geo.width() - SPRITE_WIDTH
        max_y = avail_geo.y() + avail_geo.height() - SPRITE_HEIGHT

        # Apply gravity if pet is airborne
        if self.y_pos < max_y:
            self.vy += self.gravity
            self.y_pos += self.vy
            if self.y_pos >= max_y:
                self.y_pos = max_y
                self.vy = 0
                if self.current_anim == "jump":
                    self.set_animation("idle")
        else:
            self.y_pos = max_y
            self.vy = 0

        # Autonomous Wander Logic
        if self.mode == "wander" and self.y_pos == max_y:
            self.wander_timer -= 1
            if self.wander_timer <= 0:
                self.wander_timer = random.randint(60, 180) # 1 - 3 seconds
                roll = random.random()
                if roll < 0.4:
                    self.wander_direction = 0
                    self.set_animation("idle")
                elif roll < 0.7:
                    self.wander_direction = -1
                    self.set_animation("running_left")
                else:
                    self.wander_direction = 1
                    self.set_animation("running_right")

                # 15% chance to jump
                if random.random() < 0.15:
                    self.vy = -10
                    self.set_animation("jump")

            # Execute walk movement
            if self.wander_direction != 0 and self.current_anim != "jump":
                self.vx = self.wander_direction * 1.5
                self.x_pos += self.vx
            else:
                self.vx = 0

            # Stay inside work area bounds
            if self.x_pos < min_x:
                self.x_pos = min_x
                self.wander_direction = 1
                self.set_animation("running_right")
            elif self.x_pos > max_x:
                self.x_pos = max_x
                self.wander_direction = -1
                self.set_animation("running_left")

        self.move(int(self.x_pos), int(self.y_pos))

    # Mouse Drag Interactions
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            # Store drag offset
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self.set_animation("jump")
            event.accept()

    def mouseMouseMoveEvent(self, event):
        # Fallback or overrides for older Qt version mouse events
        pass

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_offset
            
            # Constrain window inside primary monitor workspace bounds during drag
            avail_geo = QApplication.primaryScreen().availableGeometry()
            new_x = max(avail_geo.x(), min(new_pos.x(), avail_geo.x() + avail_geo.width() - SPRITE_WIDTH))
            new_y = max(avail_geo.y(), min(new_pos.y(), avail_geo.y() + avail_geo.height() - SPRITE_HEIGHT))
            
            self.x_pos = new_x
            self.y_pos = new_y
            self.move(new_x, new_y)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.vy = 0  # Let gravity pull it down from release height
            event.accept()

    # Context Menu Actions
    def show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0f1219;
                color: #f1f5f9;
                border: 1px solid #00f2fe;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: rgba(0, 242, 254, 0.15);
                color: #00f2fe;
            }
        """)

        # Quick Actions
        wave_act = QAction("👋 Wave", self)
        wave_act.triggered.connect(lambda: self.set_animation("wave"))
        
        pet_act = QAction("❤️ Pet (Beep!)", self)
        pet_act.triggered.connect(lambda: self.set_animation("wave"))

        failed_act = QAction("⚠️ Simulate Error", self)
        failed_act.triggered.connect(lambda: self.set_animation("failed"))

        exit_act = QAction("❌ Close Companion", self)
        exit_act.triggered.connect(QApplication.instance().quit)

        menu.addAction(wave_act)
        menu.addAction(pet_act)
        menu.addAction(failed_act)
        menu.addSeparator()

        # Behavior select
        mode_menu = menu.addMenu("🎯 Behavior Mode")
        mode_menu.setStyleSheet(menu.styleSheet())
        
        wander_act = QAction("Autopilot Wander", self)
        wander_act.setCheckable(True)
        wander_act.setChecked(self.mode == "wander")
        wander_act.triggered.connect(lambda: self.set_mode_str("wander"))

        idle_act = QAction("Static Idle", self)
        idle_act.setCheckable(True)
        idle_act.setChecked(self.mode == "idle")
        idle_act.triggered.connect(lambda: self.set_mode_str("idle"))

        mode_menu.addAction(wander_act)
        mode_menu.addAction(idle_act)

        menu.addSeparator()
        menu.addAction(exit_act)
        menu.exec(self.mapToGlobal(pos))

    def set_mode_str(self, val):
        self.mode = val
        if val == "idle":
            self.set_animation("idle")
            self.wander_direction = 0

    # Backend Connection commands
    def handle_backend_command(self, cmd_str):
        print(f"[Companion] Received command: {cmd_str}")
        if ":" in cmd_str:
            target, val = cmd_str.split(":", 1)
            target = target.strip().lower()
            val = val.strip().lower()

            if target == "animation":
                if val in self.anims:
                    self.set_animation(val)
            elif target == "mode":
                if val in ["wander", "idle"]:
                    self.set_mode_str(val)

    def closeEvent(self, event):
        self.listener.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Target path for spritesheet
    base_dir = os.path.dirname(os.path.abspath(__file__))
    spritesheet_path = os.path.join(base_dir, "robot", "spritesheet.webp")
    
    try:
        anims = load_animations(spritesheet_path)
    except Exception as e:
        print(f"Error loading spritesheet assets: {e}")
        return
        
    pet = DesktopPet(anims)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
