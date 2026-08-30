import random
import time
import datetime
from PySide6.QtWidgets import QWidget, QLabel, QMenu, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QAction, QGuiApplication

from src.vision_pet.client.listener import BackendListener
from src.vision_pet.client.utils import ANIMATIONS
from src.vision_pet.client.monitor import SystemMonitor
from src.vision_pet.client.speech_bubble import SpeechBubble

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

        # Physics/Wander update loop.
        # Runs at ~60fps (16ms) only while the pet is actually moving; drops to
        # ~15fps (66ms) when static/idle to cut idle CPU. Motion speed and wander
        # timing are kept identical by driving them from elapsed milliseconds, not
        # tick counts, so the slower cadence changes nothing visually.
        self._phys_fast_ms = 16
        self._phys_idle_ms = 66
        self._phys_interval = self._phys_fast_ms
        # Cached available screen geometry (querying it 60x/sec is wasteful; it
        # only changes on resolution/taskbar changes, so refresh ~1x/sec).
        self._geo_cache = None
        self._geo_ttl = 0
        self.physics_timer = QTimer(self)
        self.physics_timer.timeout.connect(self.update_physics_loop)
        self.physics_timer.start(self._phys_interval)

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
            "bluetooth": "Unknown",
            "muted": None,
        }
        self.backend_override = False

        # --- Single-source-of-truth reaction state ---
        # The client is now the ONLY monitor (the standalone backend daemon is
        # legacy/optional), so it must detect transition events itself instead
        # of relying on a second process. These track prior samples so we can
        # fire one-shot confirmation animations on edges.
        self._metrics_primed = False      # first sample just sets a baseline
        self._bedtime_announced = False    # need_to_go_bed fires once per night

        # Inactivity tracking drives the very_tired -> need_rest -> sleeping
        # sequence during the day (docs described it; only clock-based night
        # mode existed before).
        self.last_activity = time.monotonic()
        self.INACTIVITY_SLEEP_S = 300      # 5 minutes idle -> drift to sleep

        # Initialize background system monitor
        self.monitor = SystemMonitor()
        self.monitor.metrics_updated.connect(self.handle_system_metrics)
        self.monitor.start()

        # Speech bubble for AI/`say:` messages (floats above the pet)
        self.speech_bubble = SpeechBubble()

        # Initial placement on desktop screen
        if self.gravity_enabled:
            self.snap_to_bottom()
        else:
            self.snap_to_center()
        self.show()

    def _current_screen(self):
        """Return the screen the pet currently sits on (multi-monitor aware).

        Falls back to the window's own screen, then the primary screen, if the
        pet's center is between/outside displays.
        """
        center = QPoint(int(self.x_pos + self.sprite_width / 2),
                        int(self.y_pos + self.sprite_height / 2))
        screen = QGuiApplication.screenAt(center)
        if screen is None:
            screen = self.screen() or QApplication.primaryScreen()
        return screen

    def _avail_geo(self, fresh=False):
        """Returns cached available geometry of the pet's *current* screen.

        Refreshed roughly once per second (or immediately when ``fresh=True``)
        instead of on every physics tick, so we avoid ~60 screen queries per
        second while still supporting multiple monitors of different sizes.
        """
        if fresh or self._geo_cache is None or self._geo_ttl <= 0:
            self._geo_cache = self._current_screen().availableGeometry()
            self._geo_ttl = 60  # ~1s worth of ticks
        self._geo_ttl -= 1
        return self._geo_cache

    def snap_to_bottom(self):
        """Snaps the pet immediately to the bottom of the screen taskbar work-area."""
        avail_geo = self._avail_geo(fresh=True)
        self.x_pos = (avail_geo.width() - self.sprite_width) // 2 + avail_geo.x()
        self.y_pos = avail_geo.height() - self.sprite_height + avail_geo.y()
        self.move(int(self.x_pos), int(self.y_pos))

    def snap_to_center(self):
        """Snaps the pet immediately to the center of the screen."""
        avail_geo = self._avail_geo(fresh=True)
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
        """Single source of truth for automatic reactions.

        Detects transition *events* (one-shot confirmations) then falls back to
        steady-state priority reactions. This absorbs the work the separate
        backend daemon used to do, so only one process/monitor runs and the two
        can no longer race each other.
        """
        prev = self.latest_metrics
        self.latest_metrics = metrics

        # Manual/AI override suppresses all automatic reactions
        if self.backend_override:
            return

        # First sample only establishes a baseline (mirrors daemon startup).
        if not self._metrics_primed:
            self._metrics_primed = True
            self._apply_steady_state(metrics)
            return

        # --- Transition events (edge-triggered one-shots) ---
        online = metrics["wifi_status"] == "Connected"
        was_online = prev.get("wifi_status") == "Connected"
        if online and not was_online:
            # Internet just came back -> reconnect confirmation (one-shot)
            self.set_animation("wifi_connected")
            return

        if metrics["is_charging"] and metrics["battery"] >= 100 and prev.get("battery", 100) < 100:
            # Battery just topped off while plugged in -> celebrate once
            self.set_animation("charged_filled")
            return

        muted, prev_muted = metrics.get("muted"), prev.get("muted")
        if muted is not None and prev_muted is not None and muted != prev_muted:
            # System volume mute just toggled (only if audio monitoring works)
            self.set_animation("muted" if muted else "unmuted")
            return

        # --- Steady-state priority reactions ---
        self._apply_steady_state(metrics)

    def _apply_steady_state(self, metrics):
        """Priority-ordered reaction to the *current* system state."""
        # Wi-Fi / network down -> "wifi_disconnected"
        if metrics["wifi_status"] != "Connected":
            self.set_animation("wifi_disconnected")
        # CPU or RAM under heavy load -> "running" (working hard)
        elif metrics["cpu"] > 75.0 or metrics["ram"] > 90.0:
            self.set_animation("running")
        # Battery low and unplugged (< 20%) -> "need_charging"
        elif metrics["battery"] < 20 and not metrics["is_charging"]:
            if self.current_anim not in ["need_charging", "charging", "idle_charged"]:
                self.set_animation("need_charging")
        # Charging but not full -> "charging" or "idle_charged"
        elif metrics["is_charging"] and metrics["battery"] < 100:
            if metrics["battery"] > 85:
                if self.current_anim not in ["idle_charged", "running_left", "running_right", "jump"]:
                    self.set_animation("idle_charged")
            else:
                if self.current_anim not in ["charging", "running_left", "running_right", "jump"]:
                    self.set_animation("charging")
        # Battery fully charged and plugged in -> "charged_filled"
        elif metrics["is_charging"] and metrics["battery"] == 100:
            if self.current_anim not in ["charged_filled", "charged_disconnected", "running_left", "running_right", "jump"]:
                self.set_animation("charged_filled")
        # Battery fully charged but unplugged -> "charged_disconnected"
        elif not metrics["is_charging"] and metrics["battery"] == 100:
            if self.current_anim not in ["charged_disconnected", "running_left", "running_right", "jump"]:
                self.set_animation("charged_disconnected")
        # Otherwise: night schedule / inactivity drift / normal idle
        else:
            self._apply_rest_state()

    def _apply_rest_state(self):
        """Sleep/tired lifecycle driven by clock time and inactivity."""
        hour = datetime.datetime.now().hour
        is_night = (hour >= 22 or hour < 6)
        rest_states = ["very_tired", "need_rest", "sleeping", "need_to_go_bed"]

        if is_night:
            if not self._bedtime_announced:
                # One-shot bedtime reminder, then chains through to sleeping.
                self._bedtime_announced = True
                self.set_animation("need_to_go_bed")
            elif self.mode == "idle":
                if self.current_anim != "sleeping":
                    self.set_animation("sleeping")
            else:
                if self.current_anim not in rest_states:
                    self.set_animation("very_tired")  # chains -> need_rest -> sleeping
        else:
            self._bedtime_announced = False  # reset for the next night
            idle_for = time.monotonic() - self.last_activity
            if idle_for >= self.INACTIVITY_SLEEP_S:
                # Long daytime inactivity -> drift toward sleep.
                if self.current_anim not in rest_states:
                    self.set_animation("very_tired")
            elif self.current_anim in ["wifi_disconnected", "running", "failed", "charging",
                                        "charged_disconnected", "charged_filled", "need_charging",
                                        "wifi_connected", "sleeping", "very_tired", "need_rest",
                                        "need_to_go_bed", "idle_charged", "muted", "unmuted"]:
                self.set_animation("idle")

    def _mark_activity(self):
        """Record user/AI interaction; wakes the pet if it was resting."""
        self.last_activity = time.monotonic()
        self._bedtime_announced = False
        if not self.backend_override and self.current_anim in ["sleeping", "very_tired", "need_rest", "need_to_go_bed"]:
            self.set_animation("idle")

    def show_speech(self, text, duration_ms=4000):
        """Show a short message in the speech bubble above the pet."""
        self._mark_activity()
        self.speech_bubble.show_message(text, duration_ms)
        self._reposition_bubble()

    def _reposition_bubble(self):
        """Keep the speech bubble anchored above the pet as it moves."""
        if self.speech_bubble.isVisible():
            self.speech_bubble.reposition(self.x_pos, self.y_pos,
                                          self.sprite_width, self._avail_geo())

    def trigger_manual_animation(self, name):
        """Triggers manual user/backend animation override."""
        self._mark_activity()
        self.backend_override = True
        self.set_animation(name)

    def update_physics_loop(self):
        """Main engine tick. Handles gravity, bounds, and wander behaviors.

        Runs at up to ~60fps while moving and throttles down to ~15fps while
        static. All motion and timing are expressed in milliseconds so the
        variable tick rate does not change movement speed or wander cadence.
        """
        if self.is_dragging:
            return

        avail_geo = self._avail_geo()
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
        is_special_state = self.current_anim not in ["idle", "running_right", "running_left", "waiting", "running", "charging", "idle_charged", "charged_disconnected"]

        if self.mode == "wander" and not self.backend_override and not is_special_state and (not self.gravity_enabled or self.y_pos == max_y):
            self.wander_timer -= self._phys_interval
            if self.wander_timer <= 0:
                self.wander_timer = random.randint(960, 2880)  # ~1 - 3 seconds (ms)
                
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
                    if self.latest_metrics.get("is_charging", False):
                        if self.latest_metrics.get("battery", 100) > 85:
                            self.set_animation("idle_charged")
                        else:
                            self.set_animation("charging")
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
        else:
            self.wander_direction = 0
            self.wander_direction_y = 0
            self.vx = 0
            if not self.gravity_enabled or self.y_pos == max_y:
                self.vy = 0

        # Adaptive tick rate: run fast only while actually moving or airborne,
        # otherwise throttle down to save CPU. Motion/wander are ms-driven so
        # this never alters visible speed or timing.
        airborne = self.gravity_enabled and self.y_pos < max_y
        moving = (self.vx != 0 or self.vy != 0
                  or self.wander_direction != 0 or self.wander_direction_y != 0)
        desired = self._phys_fast_ms if (airborne or moving) else self._phys_idle_ms
        if desired != self._phys_interval:
            self._phys_interval = desired
            self.physics_timer.setInterval(desired)

        self.move(int(self.x_pos), int(self.y_pos))
        self._reposition_bubble()

    # Mouse Drag Interactions
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mark_activity()
            self.is_dragging = True
            # Store drag offset
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self.set_animation("jump")
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_offset

            # Constrain to the workspace of whichever monitor the pet is now on.
            # Fresh lookup lets the pet adopt a new screen as it's dragged across.
            avail_geo = self._avail_geo(fresh=True)
            new_x = max(avail_geo.x(), min(new_pos.x(), avail_geo.x() + avail_geo.width() - self.sprite_width))
            new_y = max(avail_geo.y(), min(new_pos.y(), avail_geo.y() + avail_geo.height() - self.sprite_height))

            self.x_pos = new_x
            self.y_pos = new_y
            self.move(new_x, new_y)
            self._reposition_bubble()
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.vy = 0  # Let gravity pull it down from release height
            # Invalidate cached geometry so the next tick re-resolves the
            # current monitor (the pet may have crossed screens while dragging).
            self._geo_ttl = 0
            # Resume fast ticks immediately so a post-release fall is smooth.
            if self._phys_interval != self._phys_fast_ms:
                self._phys_interval = self._phys_fast_ms
                self.physics_timer.setInterval(self._phys_fast_ms)
            event.accept()

    # Context Menu Actions
    def show_context_menu(self, pos):
        self._mark_activity()
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
        exit_act.triggered.connect(self.shutdown)

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
        self._mark_activity()
        self.mode = val
        if val == "idle":
            self.set_animation("idle")
            self.wander_direction = 0
            self.wander_direction_y = 0

    # Backend Connection commands
    def handle_backend_command(self, cmd_str):
        print(f"[Companion] Received command: {cmd_str}")
        self._mark_activity()
        if ":" in cmd_str:
            target, val = cmd_str.split(":", 1)
            target = target.strip().lower()
            # Preserve the original (case-sensitive) value for commands like
            # `say:` that carry human-readable text; lowercase only for the
            # keyword-style commands compared below.
            raw_val = val.strip()
            val = raw_val.lower()

            if target == "say":
                # Show a short message bubble above the pet. Keeps original case.
                self.show_speech(raw_val)
            elif target == "animation":
                if val in self.anims:
                    # Set manual override when backend requests a specific animation
                    self.backend_override = True
                    self.set_animation(val)
            elif target == "mode":
                if val in ["wander", "idle"]:
                    # Reset manual override when backend changes mode
                    self.backend_override = False
                    self.set_mode_str(val)
            elif target == "state":
                # Semantic AI-workflow states. Busy holds (looping) until the
                # next state/override; success/error are one-shot and release
                # the override automatically when they finish playing.
                state_map = {"busy": "waiting", "success": "review", "error": "failed"}
                if val == "idle":
                    self.backend_override = False
                    self.set_animation("idle")
                elif val in state_map:
                    self.backend_override = True
                    self.set_animation(state_map[val])
            elif target == "override":
                # Allow the backend/AI to release (or re-lock) its hold so that
                # automatic system reactions resume. Without this, a looping
                # animation would leave backend_override stuck on forever.
                if val == "clear":
                    self.backend_override = False
                elif val == "lock":
                    self.backend_override = True

    def shutdown(self):
        """Cleanly stop worker threads before quitting the application.

        Wired to the 'Close Companion' menu. QApplication.quit() alone does not
        fire closeEvent(), so the listener/monitor threads would otherwise be
        left running (QThread destroyed-while-running warning / hang on exit).
        """
        self.listener.stop()
        self.monitor.stop()
        self.speech_bubble.dismiss()
        QApplication.instance().quit()

    def closeEvent(self, event):
        self.listener.stop()
        self.monitor.stop()
        self.speech_bubble.close()
        event.accept()
