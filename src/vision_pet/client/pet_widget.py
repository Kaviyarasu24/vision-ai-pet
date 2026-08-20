import random
from PySide6.QtWidgets import QWidget, QLabel, QMenu, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QAction

from src.vision_pet.client.listener import BackendListener
from src.vision_pet.client.utils import ANIMATIONS
from src.vision_pet.client.monitor import SystemMonitor

class DesktopPet(QWidget):
    """The frameless, transparent QWidget desktop pet client."""
    def __init__(self, anims, width, height):
        super().__init__()
        self.anims = anims
        self.sprite_width = width
        self.sprite_height = height

        # Window styling: frameless, stay on top, hide taskbar entry (Tool window)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # UI Elements
        self.label = QLabel(self)
        self.label.setFixedSize(self.sprite_width, self.sprite_height)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setScaledContents(False)
        self.setFixedSize(self.sprite_width, self.sprite_height)

        # Physics & Position States
        self.x_pos = 200
        self.y_pos = 200
        self.vx = 0
        self.vy = 0
        self.gravity = 0.8
        self.gravity_enabled = False  # Set to False by default so it can be placed freely on the screen
        self.wander_direction_y = 0
        self.is_dragging = False
        self.drag_offset = QPoint()

        # Behavior States
        self.mode = "wander"  # "wander", "idle"
        self.wander_timer = 0
        self.wander_direction = 0  # -1: left, 1: right, 0: idle

        # Animation states
        self.current_anim = "welcoming"
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

        # Initialize system metrics state
        self.latest_metrics = {
            "cpu": 0.0,
            "ram": 0.0,
            "battery": 100,
            "is_charging": True,
            "wifi_status": "Disconnected",
            "wifi_name": None,
            "bluetooth": "Unknown"
        }
        self.backend_override = False

        # Initialize background system monitor
        self.monitor = SystemMonitor()
        self.monitor.metrics_updated.connect(self.handle_system_metrics)
        self.monitor.start()

        # Initial placement on desktop screen
        if self.gravity_enabled:
            self.snap_to_bottom()
        else:
            self.snap_to_center()
        self.show()

    def snap_to_bottom(self):
        """Snaps the pet immediately to the bottom of the screen taskbar work-area."""
        avail_geo = QApplication.primaryScreen().availableGeometry()
        self.x_pos = (avail_geo.width() - self.sprite_width) // 2 + avail_geo.x()
        self.y_pos = avail_geo.height() - self.sprite_height + avail_geo.y()
        self.move(int(self.x_pos), int(self.y_pos))

    def snap_to_center(self):
        """Snaps the pet immediately to the center of the screen."""
        avail_geo = QApplication.primaryScreen().availableGeometry()
        self.x_pos = (avail_geo.width() - self.sprite_width) // 2 + avail_geo.x()
        self.y_pos = (avail_geo.height() - self.sprite_height) // 2 + avail_geo.y()
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
                # Clear manual backend/UI override when a non-looping animation completes
                self.backend_override = False
                self.set_animation(next_state)
                return
        self.update_sprite_display()

    def update_sprite_display(self):
        """Updates UI label pixmap."""
        pixmap = self.anims[self.current_anim][self.current_frame]
        self.label.setPixmap(pixmap)

    def handle_system_metrics(self, metrics):
        """Processes live system metrics and updates pet visual state accordingly."""
        self.latest_metrics = metrics
        
        # If backend or context menu override is active, skip system monitor reactions
        if self.backend_override:
            return

        # Determine reaction animation
        # Wi-Fi Disconnected -> "wifi_disconnected"
        if metrics["wifi_status"] == "Disconnected":
            self.set_animation("wifi_disconnected")
        # CPU > 75% -> "running" (computing intensely)
        elif metrics["cpu"] > 75.0:
            self.set_animation("running")
        # Battery low and unplugged (< 20%) -> "need_charging"
        elif metrics["battery"] < 20 and not metrics["is_charging"]:
            self.set_animation("need_charging")
        # Charging but not full -> "charging"
        elif metrics["is_charging"] and metrics["battery"] < 100:
            self.set_animation("charging")
        # Battery fully charged and plugged in -> "charged_filled"
        elif metrics["is_charging"] and metrics["battery"] == 100:
            self.set_animation("charged_filled")
        # Battery fully charged but unplugged -> "charged_disconnected"
        elif not metrics["is_charging"] and metrics["battery"] == 100:
            self.set_animation("charged_disconnected")
        # Otherwise, check night status for sleep/tired state, or revert to normal idle/wander
        else:
            import datetime
            hour = datetime.datetime.now().hour
            is_night = (hour >= 22 or hour < 6)
            
            if is_night:
                if self.mode == "idle":
                    self.set_animation("sleeping")
                else:
                    self.set_animation("very_tired")
            else:
                if self.current_anim in ["wifi_disconnected", "running", "failed", "charging", "charged_disconnected", "charged_filled", "need_charging", "wifi_connected", "sleeping", "very_tired", "need_rest", "need_to_go_bed"]:
                    if self.mode == "idle":
                        self.set_animation("idle")
                    else:
                        # Let wander logic/physics naturally handle animations
                        pass

    def trigger_manual_animation(self, name):
        """Triggers manual user/backend animation override."""
        self.backend_override = True
        self.set_animation(name)

    def update_physics_loop(self):
        """Main engine tick running at 60 FPS. Handles gravity, bounds, and wander behaviors."""
        if self.is_dragging:
            return

        avail_geo = QApplication.primaryScreen().availableGeometry()
        min_x = avail_geo.x()
        max_x = avail_geo.x() + avail_geo.width() - self.sprite_width
        min_y = avail_geo.y()
        max_y = avail_geo.y() + avail_geo.height() - self.sprite_height

        # Apply gravity/airborne check if gravity is enabled
        if self.gravity_enabled:
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
        else:
            # Maintain screen boundary safety when floating/dragging without gravity
            if self.y_pos < min_y:
                self.y_pos = min_y
                self.vy = 0
            elif self.y_pos > max_y:
                self.y_pos = max_y
                self.vy = 0

        # Autonomous Wander Logic
        if self.mode == "wander" and (not self.gravity_enabled or self.y_pos == max_y):
            self.wander_timer -= 1
            if self.wander_timer <= 0:
                self.wander_timer = random.randint(60, 180) # 1 - 3 seconds
                
                # Roll for horizontal movement
                roll_x = random.random()
                if roll_x < 0.4:
                    self.wander_direction = 0
                elif roll_x < 0.7:
                    self.wander_direction = -1
                else:
                    self.wander_direction = 1

                # Roll for vertical movement if floating
                if not self.gravity_enabled:
                    roll_y = random.random()
                    if roll_y < 0.4:
                        self.wander_direction_y = 0
                    elif roll_y < 0.7:
                        self.wander_direction_y = -1
                    else:
                        self.wander_direction_y = 1
                else:
                    self.wander_direction_y = 0

                # Determine sprite animation
                if self.wander_direction == -1:
                    self.set_animation("running_left")
                elif self.wander_direction == 1:
                    self.set_animation("running_right")
                else:
                    if not self.gravity_enabled and self.wander_direction_y != 0:
                        self.set_animation("waiting" if random.random() < 0.5 else "idle")
                    else:
                        self.set_animation("idle")

                # 15% chance to jump (only on taskbar floor)
                if self.gravity_enabled and random.random() < 0.15:
                    self.vy = -10
                    self.set_animation("jump")

            # Execute movement
            if self.gravity_enabled:
                if self.wander_direction != 0 and self.current_anim != "jump":
                    self.vx = self.wander_direction * 1.5
                    self.x_pos += self.vx
                else:
                    self.vx = 0
            else:
                self.vx = self.wander_direction * 1.2
                self.vy = self.wander_direction_y * 1.2
                self.x_pos += self.vx
                self.y_pos += self.vy

            # Stay inside work area bounds
            if self.x_pos < min_x:
                self.x_pos = min_x
                self.wander_direction = 1
                self.set_animation("running_right")
            elif self.x_pos > max_x:
                self.x_pos = max_x
                self.wander_direction = -1
                self.set_animation("running_left")

            if not self.gravity_enabled:
                if self.y_pos < min_y:
                    self.y_pos = min_y
                    self.wander_direction_y = 1
                elif self.y_pos > max_y:
                    self.y_pos = max_y
                    self.wander_direction_y = -1

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
            new_x = max(avail_geo.x(), min(new_pos.x(), avail_geo.x() + avail_geo.width() - self.sprite_width))
            new_y = max(avail_geo.y(), min(new_pos.y(), avail_geo.y() + avail_geo.height() - self.sprite_height))
            
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

        # System Monitoring Dashboard (Live Stats Labels)
        stats_title = QAction("📋 System Monitor Info", self)
        stats_title.setEnabled(False)
        menu.addAction(stats_title)
        
        cpu_act = QAction(f"  ⚙️ CPU Usage: {self.latest_metrics['cpu']:.1f}%", self)
        cpu_act.setEnabled(False)
        menu.addAction(cpu_act)

        bat_text = f"  🔋 Battery: {self.latest_metrics['battery']}%"
        if self.latest_metrics['is_charging']:
            bat_text += " (Charging)"
        else:
            bat_text += " (Discharging)"
        bat_act = QAction(bat_text, self)
        bat_act.setEnabled(False)
        menu.addAction(bat_act)

        wifi_text = f"  📶 Wi-Fi: {self.latest_metrics['wifi_status']}"
        if self.latest_metrics['wifi_name']:
            wifi_text += f" ({self.latest_metrics['wifi_name']})"
        wifi_act = QAction(wifi_text, self)
        wifi_act.setEnabled(False)
        menu.addAction(wifi_act)

        bt_act = QAction(f"  🔵 Bluetooth: {self.latest_metrics['bluetooth']}", self)
        bt_act.setEnabled(False)
        menu.addAction(bt_act)

        menu.addSeparator()

        # Quick Actions
        wave_act = QAction("👋 Wave", self)
        wave_act.triggered.connect(lambda: self.trigger_manual_animation("wave"))
        
        pet_act = QAction("❤️ Pet (Beep!)", self)
        pet_act.triggered.connect(lambda: self.trigger_manual_animation("wave"))

        failed_act = QAction("⚠️ Simulate Error", self)
        failed_act.triggered.connect(lambda: self.trigger_manual_animation("failed"))

        exit_act = QAction("❌ Close Companion", self)
        exit_act.triggered.connect(QApplication.instance().quit)

        menu.addAction(wave_act)
        menu.addAction(pet_act)
        menu.addAction(failed_act)
        
        # Triggerable Animations Submenu
        anim_menu = menu.addMenu("🎭 Trigger Animation")
        anim_menu.setStyleSheet(menu.styleSheet())
        
        for anim_name in ["welcoming", "charging", "charged_disconnected", "charged_filled", "need_charging", "wifi_connected", "wifi_disconnected", "muted", "unmuted", "very_tired", "need_rest", "sleeping", "need_to_go_bed"]:
            label = anim_name.replace("_", " ").capitalize()
            if anim_name == "welcoming":
                label = "👋 Welcoming"
            elif anim_name == "charging":
                label = "⚡ Charging"
            elif anim_name == "charged_disconnected":
                label = "🔌 Charged & Disconnected"
            elif anim_name == "charged_filled":
                label = "🔋 Charged & Filled"
            elif anim_name == "need_charging":
                label = "🪫 Need Charging"
            elif anim_name == "wifi_connected":
                label = "📶 Wi-Fi Connected"
            elif anim_name == "wifi_disconnected":
                label = "🚫 Wi-Fi Disconnected"
            elif anim_name == "muted":
                label = "🔇 Muted"
            elif anim_name == "unmuted":
                label = "🔊 Unmuted"
            elif anim_name == "very_tired":
                label = "💤 Very Tired"
            elif anim_name == "need_rest":
                label = "🥱 Need Rest"
            elif anim_name == "sleeping":
                label = "😴 Sleeping"
            elif anim_name == "need_to_go_bed":
                label = "🛌 Need to go to Bed"
                
            act = QAction(label, self)
            act.triggered.connect(lambda checked=False, name=anim_name: self.trigger_manual_animation(name))
            anim_menu.addAction(act)

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

        # Screen Placement / Physics select
        placement_menu = menu.addMenu("📍 Screen Placement")
        placement_menu.setStyleSheet(menu.styleSheet())

        free_act = QAction("Float Freely", self)
        free_act.setCheckable(True)
        free_act.setChecked(not self.gravity_enabled)
        free_act.triggered.connect(lambda: self.set_gravity_enabled(False))

        taskbar_act = QAction("Constrain to Taskbar", self)
        taskbar_act.setCheckable(True)
        taskbar_act.setChecked(self.gravity_enabled)
        taskbar_act.triggered.connect(lambda: self.set_gravity_enabled(True))

        placement_menu.addAction(free_act)
        placement_menu.addAction(taskbar_act)

        menu.addSeparator()
        menu.addAction(exit_act)
        menu.exec(self.mapToGlobal(pos))

    def set_gravity_enabled(self, enabled):
        self.gravity_enabled = enabled
        if enabled:
            # Let it fall down naturally if enabled
            self.vy = 0
        else:
            self.wander_direction_y = 0

    def set_mode_str(self, val):
        self.mode = val
        if val == "idle":
            self.set_animation("idle")
            self.wander_direction = 0
            self.wander_direction_y = 0

    # Backend Connection commands
    def handle_backend_command(self, cmd_str):
        print(f"[Companion] Received command: {cmd_str}")
        if ":" in cmd_str:
            target, val = cmd_str.split(":", 1)
            target = target.strip().lower()
            val = val.strip().lower()

            if target == "animation":
                if val in self.anims:
                    # Set manual override when backend requests a specific animation
                    self.backend_override = True
                    self.set_animation(val)
            elif target == "mode":
                if val in ["wander", "idle"]:
                    # Reset manual override when backend changes mode
                    self.backend_override = False
                    self.set_mode_str(val)

    def closeEvent(self, event):
        self.listener.stop()
        self.monitor.stop()
        event.accept()
