import random
from PySide6.QtWidgets import QWidget, QLabel, QMenu, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QAction

from src.vision_pet.client.listener import BackendListener
from src.vision_pet.client.utils import ANIMATIONS, SPRITE_WIDTH, SPRITE_HEIGHT

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
