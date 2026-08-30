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


# --- AI assistant integration helpers ---
# Convenience wrappers mapping high-level AI workflow states onto the pet's
# semantic `state:` TCP command. Import these from your agent/assistant code:
#
#     from src.vision_pet.backend.stub import notify_task_started, notify_task_completed
#
# The client maps busy -> waiting (loops until cleared), success -> review and
# error -> failed (one-shot, auto-releasing). Call notify_idle() when done.

def notify_task_started():
    """Signal that the AI is working — shows the looping `waiting` animation."""
    return send_command("state:busy")


def notify_task_completed():
    """Signal success — plays the one-shot `review` animation, then resumes."""
    return send_command("state:success")


def notify_task_failed():
    """Signal an error — plays the one-shot `failed` animation, then resumes."""
    return send_command("state:error")


def notify_idle():
    """Release any AI hold and return the pet to automatic behavior."""
    return send_command("state:idle")


def say(text):
    """Show a short message in a speech bubble above the pet.

    The message auto-dismisses after a few seconds. Newlines and colons in the
    text are preserved (only the leading `say:` prefix is stripped by the pet).
    """
    return send_command(f"say:{text}")

