import socket
import time

def send_command(command):
    """Sends a state change command to the running Desktop Pet on localhost:5050."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", 5050))
        s.sendall(command.encode('utf-8'))
        response = s.recv(1024).decode('utf-8').strip()
        print(f"Sent: '{command}' | Server Response: '{response}'")
        s.close()
    except ConnectionRefusedError:
        print("Could not connect to Desktop Pet: Connection refused.")
        print("Please verify that desktop_pet.py is running and listening on port 5050.")
    except Exception as e:
        print(f"Error communicating with Desktop Pet: {e}")

if __name__ == "__main__":
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
