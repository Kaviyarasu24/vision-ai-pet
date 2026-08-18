import sys
import os

# Disable high-DPI scaling rounding issues that cause size jitter/shaking on Windows
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

from PySide6.QtWidgets import QApplication

from src.vision_pet.client.pet_widget import DesktopPet
from src.vision_pet.client.utils import load_animations

def main():
    app = QApplication(sys.argv)
    
    # Resolve assets path relative to this file
    # __file__ is in d:\MCP\src\vision_pet\client\__main__.py
    client_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(client_dir, "..", "..", ".."))
    spritesheet_path = os.path.join(project_root, "assets", "robot", "spritesheet.webp")
    
    try:
        anims = load_animations(spritesheet_path)
    except Exception as e:
        print(f"Error loading spritesheet assets from path: {spritesheet_path}")
        print(f"Details: {e}")
        return 1
        
    pet = DesktopPet(anims)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
