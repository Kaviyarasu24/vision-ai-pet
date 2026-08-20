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
    "failed": {"row": 5, "frames": 8, "speed": 150, "loop": False, "next": "idle"},
    "waiting": {"row": 6, "frames": 6, "speed": 180, "loop": True},
    "running": {"row": 7, "frames": 6, "speed": 100, "loop": True},
    "review": {"row": 8, "frames": 6, "speed": 200, "loop": False, "next": "idle"},
    
    # User-defined mappings from newimage.webp (Rows 10 to 22 mapped to 0-based indices 9 to 21)
    "charging": {"row": 9, "frames": 6, "speed": 140, "loop": True, "next": "idle_charged"},
    "charged_disconnected": {"row": 10, "frames": 5, "speed": 200, "loop": True, "next": "idle"},
    "charged_filled": {"row": 11, "frames": 6, "speed": 130, "loop": False, "next": "charged_disconnected"},
    "need_charging": {"row": 12, "frames": 6, "speed": 160, "loop": True, "next": "charging"},
    "wifi_connected": {"row": 13, "frames": 5, "speed": 150, "loop": False, "next": "idle"},
    "wifi_disconnected": {"row": 14, "frames": 5, "speed": 180, "loop": True},
    "muted": {"row": 15, "frames": 5, "speed": 200, "loop": True},
    "unmuted": {"row": 16, "frames": 5, "speed": 150, "loop": False, "next": "idle"},
    "very_tired": {"row": 17, "frames": 6, "speed": 220, "loop": True, "next": "need_rest"},
    "need_rest": {"row": 18, "frames": 6, "speed": 220, "loop": True, "next": "sleeping"},
    "sleeping": {"row": 19, "frames": 6, "speed": 260, "loop": True},
    "need_to_go_bed": {"row": 20, "frames": 5, "speed": 200, "loop": False, "next": "sleeping"},
    "welcoming": {"row": 21, "frames": 6, "speed": 130, "loop": False, "next": "idle"},
    
    # Alias for transition fallback
    "idle_charged": {"row": 10, "frames": 5, "speed": 200, "loop": True, "next": "idle"}
}

def pil_to_pixmap(pil_img):
    """Converts a PIL Image to PySide6 QPixmap preserving alpha transparency."""
    if pil_img.mode != "RGBA":
        pil_img = pil_img.convert("RGBA")
    data = pil_img.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_img.size[0], pil_img.size[1], QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)

def load_animations(sheet_path, scale_factor=1.0):
    """Crops spritesheet frames using Pillow and loads them into a dictionary of QPixmaps, scaling them if necessary."""
    if not os.path.exists(sheet_path):
        raise FileNotFoundError(f"Spritesheet not found at: {sheet_path}")
        
    img = Image.open(sheet_path).convert("RGBA")
    anims = {}
    
    # Calculate target scaled sizes
    target_w = int(SPRITE_WIDTH * scale_factor)
    target_h = int(SPRITE_HEIGHT * scale_factor)
    
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
            if scale_factor != 1.0:
                crop_frame = crop_frame.resize((target_w, target_h), Image.Resampling.NEAREST)
            frames.append(pil_to_pixmap(crop_frame))
        anims[name] = frames
    return anims
