import sys
import subprocess


def main():
    """Launch the VISION desktop pet.

    The client is now the single source of truth for system monitoring: it
    watches CPU/RAM/battery/charger/Wi-Fi (and, optionally, audio mute) in its
    own background thread and reacts to both steady-state conditions and
    transition events. The old always-on backend polling daemon has been
    retired from the default launch path — it duplicated this monitoring in a
    second interpreter and raced the client for control of the pet.

    The `src.vision_pet.backend` package still exists as an OPTIONAL relay for
    external AI-assistant integrations (see `backend/stub.py`). Run it manually
    only if you specifically want the legacy standalone event daemon:

        python -m src.vision_pet.backend
    """
    python_executable = sys.executable

    print("[Main] Starting VISION Desktop Pet (single-process monitoring)...")
    client_process = subprocess.Popen([python_executable, "-m", "src.vision_pet.client"])

    try:
        client_process.wait()
    except KeyboardInterrupt:
        print("\n[Main] KeyboardInterrupt received. Shutting down...")
    finally:
        if client_process.poll() is None:
            print("[Main] Terminating Desktop Pet Client...")
            client_process.terminate()
            try:
                client_process.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                print("[Main] Client did not terminate gracefully. Force killing...")
                client_process.kill()
        print("[Main] Stopped.")


if __name__ == "__main__":
    main()
