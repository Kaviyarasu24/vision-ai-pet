import socket

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
        return response
    except ConnectionRefusedError:
        print("Could not connect to Desktop Pet: Connection refused.")
        print("Please verify that the desktop pet client is running and listening on port 5050.")
        return None
    except Exception as e:
        print(f"Error communicating with Desktop Pet: {e}")
        return None
