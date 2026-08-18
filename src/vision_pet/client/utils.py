import os
from PySide6.QtGui import QPixmap, QImage
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
