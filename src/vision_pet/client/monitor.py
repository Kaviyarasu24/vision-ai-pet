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

        # --- CPU/resource throttling ---
        # CPU and battery are cheap and polled every cycle. Wi-Fi (netsh) and
        # especially Bluetooth (PowerShell) spawn subprocesses, so they are
        # refreshed on a much slower schedule and cached in between. State that
        # rarely changes should not cost a process spawn every few seconds.
        self._cycle = 0
        self._wifi_every = 2      # refresh Wi-Fi every 2 cycles (~6s at 3s interval)
        self._online_every = 2    # re-check internet reachability every 2 cycles
        self._bt_every = 10       # refresh Bluetooth every 10 cycles (~30s)
        self._audio_every = 1     # mute state is cheap to read; check each cycle
        self._wifi_cache = ("Disconnected", None)
        self._bt_cache = "Unknown"
        self._muted_cache = None
        self._audio_iface = None      # cached pycaw endpoint volume interface
        self._audio_available = None  # None=unknown, True/False once probed

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

            # Query Wi-Fi info (throttled: netsh subprocess is relatively costly)
            if self._cycle % self._wifi_every == 0:
                wifi_status, wifi_name = self.get_wifi_info()

                # If netsh reports disconnected, verify general internet
                # connectivity (e.g. Ethernet) — also throttled since it can
                # block on DNS/socket calls.
                if wifi_status != "Connected" and (self._cycle % self._online_every == 0):
                    if self.check_online():
                        wifi_status = "Connected"
                        if not wifi_name:
                            wifi_name = "Ethernet / Wired"
                self._wifi_cache = (wifi_status, wifi_name)
            else:
                wifi_status, wifi_name = self._wifi_cache

            # Query Bluetooth status (heavily throttled: PowerShell spawn is the
            # single most expensive recurring call — BT state rarely changes)
            if self._cycle % self._bt_every == 0:
                self._bt_cache = self.get_bluetooth_status()
            bluetooth = self._bt_cache

            # Query audio mute state (throttled). Returns None when the optional
            # audio backend (pycaw) is unavailable, in which case the pet simply
            # never reacts to mute changes.
            if self._cycle % self._audio_every == 0:
                self._muted_cache = self.get_audio_muted()
            muted = self._muted_cache

            self._cycle += 1

            # Emit updated metrics dictionary
            metrics = {
                "cpu": cpu,
                "ram": ram,
                "battery": battery_percent,
                "is_charging": is_charging,
                "wifi_status": wifi_status,
                "wifi_name": wifi_name,
                "bluetooth": bluetooth,
                "muted": muted,
            }
            self.metrics_updated.emit(metrics)

            # Sleep in small steps so we can interrupt thread quickly
            for _ in range(int(self.interval * 10)):
                if not self.running:
                    break
                self.msleep(100)

        print("[SystemMonitor] Thread stopped.")

    def check_online(self):
        """Checks if the system is connected to the internet."""
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

    def get_audio_muted(self):
        """Return True/False if the master volume mute state can be read, else None.

        Uses the optional `pycaw` package (Windows Core Audio). If it is not
        installed or the COM call fails, returns None and the mute feature is
        silently disabled — nothing else breaks.
        """
        if sys.platform != "win32" or self._audio_available is False:
            return None
        try:
            if self._audio_iface is None:
                # Lazy, one-time import + interface acquisition.
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self._audio_iface = cast(iface, POINTER(IAudioEndpointVolume))
                self._audio_available = True
            return bool(self._audio_iface.GetMute())
        except Exception:
            # pycaw missing or COM error — disable audio monitoring permanently.
            self._audio_available = False
            self._audio_iface = None
            return None

