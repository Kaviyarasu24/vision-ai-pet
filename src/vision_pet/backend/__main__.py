import time
from src.vision_pet.backend.stub import send_command

def main():
    print("--- Desktop Pet Integration Test Stub ---")
    print("This script demonstrates a comprehensive scenario triggering all new companion animations.\n")
    
    # 1. Welcoming Greeting
    print("1. Welcoming wave...")
    send_command("animation:welcoming")
    time.sleep(4.0)

    # 2. Wifi Disconnection and Reconnection
    print("2. Simulating Wi-Fi disconnected...")
    send_command("animation:wifi_disconnected")
    time.sleep(3.0)
    
    print("3. Simulating Wi-Fi connected...")
    send_command("animation:wifi_connected")
    time.sleep(3.0)

    # 4. Mute and Unmute Toggle
    print("4. Simulating voice mute...")
    send_command("animation:muted")
    time.sleep(3.0)
    
    print("5. Simulating voice unmute...")
    send_command("animation:unmuted")
    time.sleep(3.0)

    # 5. Charging and Battery cycle
    print("6. Simulating low battery (need charging)...")
    send_command("animation:need_charging")
    time.sleep(3.0)
    
    print("7. Simulating charging...")
    send_command("animation:charging")
    time.sleep(4.0)

    print("8. Simulating charge complete (charged filled)...")
    send_command("animation:charged_filled")
    time.sleep(4.0)

    print("9. Simulating unplugged after full charge (charged disconnected)...")
    send_command("animation:charged_disconnected")
    time.sleep(3.0)

    # 6. Sleepiness and Bedtime routine
    print("10. Simulating tiredness (very tired)...")
    send_command("animation:very_tired")
    time.sleep(3.0)

    print("11. Simulating need rest...")
    send_command("animation:need_rest")
    time.sleep(3.0)

    print("12. Simulating bedtime reminder (need to go bed)...")
    send_command("animation:need_to_go_bed")
    time.sleep(4.0)

    print("13. Simulating deep sleep...")
    send_command("animation:sleeping")
    time.sleep(4.0)

    # 7. Restore Autopilot Wander
    print("14. Re-enabling autopilot wander mode...")
    send_command("mode:wander")

if __name__ == "__main__":
    main()
