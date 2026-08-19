import os
import sys
import re
import socket
import subprocess
import psutil
from PySide6.QtCore import QThread, Signal

class SystemMonitor(QThread):
    """Background thread to monitor system CPU, battery, Wi-Fi, and Bluetooth status on Windows."""
    metrics_updated = Signal(dict)

    def __init__(self, interval=3.0):
        super().__init__()
        self.interval = interval
        self.running = True

    def run(self):
        print("[SystemMonitor] Thread started.")
        while self.running:
            # Query CPU and RAM
            # Non-blocking CPU query (will return percent since last call)
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent

            # Query Battery
            battery = psutil.sensors_battery()
            if battery:
                battery_percent = int(battery.percent)
                is_charging = battery.power_plugged
            else:
                battery_percent = 100
                is_charging = True

            # Query Wi-Fi info
            wifi_status, wifi_name = self.get_wifi_info()

            # Query Bluetooth status
            bluetooth = self.get_bluetooth_status()

            # Emit updated metrics dictionary
            metrics = {
                "cpu": cpu,
                "ram": ram,
                "battery": battery_percent,
                "is_charging": is_charging,
                "wifi_status": wifi_status,
                "wifi_name": wifi_name,
                "bluetooth": bluetooth
            }
            self.metrics_updated.emit(metrics)

            # Sleep in small steps so we can interrupt thread quickly
            for _ in range(int(self.interval * 10)):
                if not self.running:
                    break
                self.msleep(100)

        print("[SystemMonitor] Thread stopped.")

    def stop(self):
        self.running = False
        self.wait()

    def get_wifi_info(self):
        """Queries Windows netsh utility to retrieve wireless status and network name (SSID)."""
        wifi_name = None
        status = "Disconnected"
        if sys.platform != "win32":
            return "Unsupported Platform", None

        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            stdout = result.stdout
            
            state_match = re.search(r"^\s*State\s*:\s*(.+)$", stdout, re.MULTILINE)
            ssid_match = re.search(r"^\s*SSID\s*:\s*(.+)$", stdout, re.MULTILINE)
            
            if state_match:
                status = state_match.group(1).strip().capitalize()
            if ssid_match:
                wifi_name = ssid_match.group(1).strip()
        except Exception as e:
            status = f"Error: {e}"
        return status, wifi_name

    def get_bluetooth_status(self):
        """Queries Windows PnpDevices via PowerShell to check if Bluetooth is Enabled or Disabled."""
        if sys.platform != "win32":
            return "Unsupported"

        try:
            # Check for active Bluetooth devices status
            result = subprocess.run(
                ["powershell", "-Command", "Get-PnpDevice -Class Bluetooth | Select-Object -Property Status"],
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            stdout = result.stdout.lower()
            
            if "ok" in stdout:
                return "Enabled"
            elif "disabled" in stdout:
                return "Disabled"
            return "Not Found"
        except Exception:
            return "Unknown"
