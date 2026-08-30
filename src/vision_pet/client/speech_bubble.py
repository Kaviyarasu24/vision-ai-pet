from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, QTimer


class SpeechBubble(QWidget):
    """A small frameless, transparent bubble that floats above the pet.

    Shows a short message (e.g. from an AI assistant via `say:<text>`) and
    auto-dismisses after a timeout. It is a separate top-level window so it can
    render above the pet's own fixed-size sprite window.
    """

    MAX_WIDTH = 260

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput  # clicks pass through
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMaximumWidth(self.MAX_WIDTH)
        self.label.setStyleSheet("""
            QLabel {
                background-color: #0f1219;
                color: #f1f5f9;
                border: 1px solid #00f2fe;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 12px;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        layout.addWidget(self.label)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.dismiss)

    def show_message(self, text, duration_ms=4000):
        """Display `text`, sizing to fit, and auto-dismiss after `duration_ms`."""
        text = (text or "").strip()
        if not text:
            self.dismiss()
            return
        self.label.setText(text)
        self.adjustSize()
        self.show()
        self.raise_()
        self._dismiss_timer.start(max(1000, duration_ms))

    def dismiss(self):
        self._dismiss_timer.stop()
        self.hide()

    def reposition(self, pet_global_x, pet_global_y, pet_width, screen_geo=None):
        """Center the bubble horizontally over the pet, sitting just above it."""
        if not self.isVisible():
            return
        bx = int(pet_global_x + (pet_width - self.width()) / 2)
        by = int(pet_global_y - self.height() - 6)
        if screen_geo is not None:
            # Keep the bubble on-screen (clamp to the pet's current display).
            bx = max(screen_geo.x(), min(bx, screen_geo.x() + screen_geo.width() - self.width()))
            by = max(screen_geo.y(), by)
        self.move(bx, by)
