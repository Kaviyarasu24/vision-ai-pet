import sys
import subprocess
import time

def main():
    # Use the current Python executable to ensure virtualenv/dependency parity
    python_executable = sys.executable

    print("[Main] Starting Desktop Pet Client...")
    client_process = subprocess.Popen([python_executable, "-m", "src.vision_pet.client"])

    # Wait for the PySide6 app to start and the socket listener to bind to port 5050
    time.sleep(2.0)

    # Check if client started successfully
    if client_process.poll() is not None:
        print("[Main] Error: Desktop Pet Client failed to start.")
        return 1

    print("[Main] Starting Integration Backend Stub...")
    backend_process = subprocess.Popen([python_executable, "-m", "src.vision_pet.backend"])

    try:
        # Wait for the backend test stub to finish its demonstration cycle
        backend_process.wait()
        print("\n[Main] Backend test sequence finished successfully.")
        print("[Main] The Desktop Pet client is still running. You can interact with it on your screen.")
        print("[Main] To close, right-click the pet and choose 'Close Companion' or press Ctrl+C in this terminal.\n")
        
        # Wait for the client window to be closed manually by the user
        client_process.wait()

    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt received. Shutting down all processes...")
    finally:
        # Ensure client process is cleaned up
        if client_process.poll() is None:
            print("[Main] Terminating Desktop Pet Client...")
            client_process.terminate()
            try:
                client_process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                print("[Main] Client did not terminate gracefully. Force killing...")
                client_process.kill()
        
        # Ensure backend process is cleaned up
        if backend_process.poll() is None:
            backend_process.terminate()
            backend_process.wait()

        print("[Main] Stopped.")

if __name__ == "__main__":
    main()
