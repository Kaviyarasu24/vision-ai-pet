import time
from src.vision_pet.backend.stub import send_command

def main():
    print("--- Desktop Pet Integration Test Stub ---")
    print("This script demonstrates how your custom Python backend can trigger states on the floating pet.\n")
    
    # 1. Trigger the Wave animation
    print("1. Triggering Wave animation...")
    send_command("animation:wave")
    time.sleep(3.0)

    # 2. Put the pet in idle mode
    print("2. Switching behavior mode to static idle...")
    send_command("mode:idle")
    time.sleep(2.0)

    # 3. Trigger wait/thinking animation (useful during backend processing)
    print("3. Triggering wait/thinking animation...")
    send_command("animation:waiting")
    time.sleep(4.0)

    # 4. Trigger review animation (useful on successful backend command execution)
    print("4. Triggering review animation...")
    send_command("animation:review")
    time.sleep(4.0)

    # 5. Restore autopilot wander mode
    print("5. Re-enabling autopilot wander mode...")
    send_command("mode:wander")

if __name__ == "__main__":
    main()
