import sys
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from src.vision_pet.client.pet_widget import DesktopPet
from src.vision_pet.client.utils import load_animations

def main():
    # Set high DPI scale factor rounding policy to Floor.
    # This rounds fractional screen scales (like 125% or 150%) down to 1.0,
    # ensuring integer scaling and eliminating coordinate rounding jitters
    # and OS-vs-Qt scaling feedback loops.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.Floor)
    
    app = QApplication(sys.argv)
    
    # Resolve assets path relative to this file
    client_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(client_dir, "..", "..", ".."))
    # Load spritesheet path dynamically from pet.json configuration
    pet_json_path = os.path.join(project_root, "assets", "robot", "pet.json")
    spritesheet_name = "combined_spritesheet.webp"
    if os.path.exists(pet_json_path):
        try:
            import json
            with open(pet_json_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                spritesheet_name = metadata.get("spritesheetPath", spritesheet_name)
        except Exception as e:
            print(f"Warning: Could not parse pet.json: {e}")
            
    spritesheet_path = os.path.join(project_root, "assets", "robot", spritesheet_name)
    
    scale_factor = 0.7
    try:
        anims = load_animations(spritesheet_path, scale_factor=scale_factor)
    except Exception as e:
        print(f"Error loading spritesheet assets from path: {spritesheet_path}")
        print(f"Details: {e}")
        return 1
        
    pet = DesktopPet(anims, int(192 * scale_factor), int(208 * scale_factor))
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
