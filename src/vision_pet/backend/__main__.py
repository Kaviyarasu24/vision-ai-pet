import time
import socket
import psutil
from src.vision_pet.backend.stub import send_command

def check_online():
    """Checks if the system is currently connected to the internet."""
    # 1. Try resolving popular domains
    for domain in ["www.google.com", "www.microsoft.com"]:
        try:
            socket.gethostbyname(domain)
            return True
        except Exception:
            pass
    # 2. Fallback to connecting to a public IP on port 80 (HTTP)
    for ip in ["1.1.1.1", "8.8.8.8"]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect((ip, 80))
            s.close()
            return True
        except Exception:
            pass
    return False

def main():
    print("==================================================")
    print("--- VISION — AI Desktop Pet Event Monitor Loop ---")
    print("==================================================")
    print("[Backend] Initializing system event monitoring daemon...")
    
    # Send welcoming wave greeting at startup
    send_command("animation:welcoming")
    time.sleep(3.0)
    
    # Initialize state variables
    last_power_plugged = None
    last_battery_percent = None
    last_online = None
    
    try:
        while True:
            # Query current metrics
            battery = psutil.sensors_battery()
            online = check_online()
            
            if battery:
                power_plugged = battery.power_plugged
                battery_percent = int(battery.percent)
            else:
                power_plugged = True
                battery_percent = 100
                
            # Print initial status details
            if last_power_plugged is None:
                print(f"[Backend] Status: Battery={battery_percent}%, Plugged={power_plugged}, Online={online}")
                last_power_plugged = power_plugged
                last_battery_percent = battery_percent
                last_online = online
                # Send initial state animations based on warning priorities
                if not online:
                    send_command("animation:wifi_disconnected")
                elif battery_percent < 20 and not power_plugged:
                    send_command("animation:need_charging")
                elif power_plugged:
                    if battery_percent == 100:
                        send_command("animation:charged_filled")
                    elif battery_percent > 85:
                        send_command("animation:idle_charged")
                    else:
                        send_command("animation:charging")
                else:
                    send_command("mode:wander")
                
            # Detect transitions/events
            # Event 1: Internet Connection Restored
            if online and not last_online:
                print("[Event] Internet connection restored!")
                send_command("animation:wifi_connected")
                time.sleep(3.0)  # Let wifi_connected animation complete playing
                if not power_plugged:
                    if battery_percent < 20:
                        send_command("animation:need_charging")
                    else:
                        print("[Event] Restoring autopilot wander mode.")
                        send_command("mode:wander")
                elif power_plugged:
                    if battery_percent == 100:
                        send_command("animation:charged_filled")
                    elif battery_percent > 85:
                        send_command("animation:idle_charged")
                    else:
                        send_command("animation:charging")
                
            # Event 2: Internet Connection Lost
            elif not online and last_online:
                print("[Event] Internet connection lost!")
                send_command("animation:wifi_disconnected")
                
            # Event 3: Charger Connected
            elif power_plugged and not last_power_plugged:
                print(f"[Event] Power charger connected! Battery at {battery_percent}%")
                if online:
                    if battery_percent == 100:
                        send_command("animation:charged_filled")
                    elif battery_percent > 85:
                        send_command("animation:idle_charged")
                    else:
                        send_command("animation:charging")
                else:
                    # Wi-Fi offline has higher priority, keep wifi_disconnected active
                    pass
                    
            # Event 4: Charger Disconnected
            elif not power_plugged and last_power_plugged:
                print(f"[Event] Power charger disconnected! Battery at {battery_percent}%")
                if online:
                    if battery_percent == 100:
                        send_command("animation:charged_disconnected")
                    elif battery_percent < 20:
                        send_command("animation:need_charging")
                    else:
                        print("[Event] Restoring autopilot wander mode.")
                        send_command("mode:wander")
                else:
                    # Keep showing wifi_disconnected warning
                    pass
                    
            # Event 5: Battery Charge Reached 100% while plugged in
            elif power_plugged and battery_percent == 100 and last_battery_percent < 100:
                print("[Event] Battery fully charged!")
                if online:
                    send_command("animation:charged_filled")
                
            # Event 6: Battery Level Dropped Below 20% warning threshold (unplugged)
            elif not power_plugged and battery_percent < 20 and last_battery_percent >= 20:
                print(f"[Event] Low battery warning! Battery at {battery_percent}%")
                if online:
                    send_command("animation:need_charging")

            # Event 7: Battery Charge Reached 85% while plugged in
            elif power_plugged and battery_percent > 85 and last_battery_percent <= 85:
                print(f"[Event] Battery charged above 85% ({battery_percent}%)")
                if online:
                    send_command("animation:idle_charged")
                
            # Update state history
            last_power_plugged = power_plugged
            last_battery_percent = battery_percent
            last_online = online
            
            # Polling delay
            time.sleep(1.5)
            
    except KeyboardInterrupt:
        print("\n[Backend] Event Monitor Loop stopped by user.")
        # Restore pet wander on stop
        send_command("mode:wander")

if __name__ == "__main__":
    main()
