import socket
from PySide6.QtCore import QThread, Signal

class BackendListener(QThread):
    """Runs a background TCP socket server to accept commands from the Python backend."""
    command_received = Signal(str)

    def __init__(self, host="127.0.0.1", port=5050):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((self.host, self.port))
            server.listen(5)
            server.settimeout(1.0) # Periodically check running state
        except Exception as e:
            print(f"[Listener] Error binding to {self.host}:{self.port}: {e}")
            return

        print(f"[Listener] Listening for commands on TCP {self.host}:{self.port}...")
        while self.running:
            try:
                conn, addr = server.accept()
            except socket.timeout:
                continue
            except Exception:
                break

            try:
                conn.settimeout(2.0)
                data = conn.recv(1024).decode('utf-8').strip()
                if data:
                    self.command_received.emit(data)
                conn.sendall(b"OK\n")
            except Exception as e:
                print(f"[Listener] Connection error: {e}")
            finally:
                conn.close()

        server.close()

    def stop(self):
        self.running = False
        self.wait()
