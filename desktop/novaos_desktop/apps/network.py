# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Network - a real Wi-Fi manager for NovaOS Desktop, backed by nmcli.

This actually controls the host's networking through NetworkManager (nmcli):
show status, scan for Wi-Fi networks, connect (with a password prompt for
secured ones), disconnect, and toggle the radio. All nmcli calls run on
background threads so the desktop never freezes; results come back via signals.

If nmcli is unavailable the app shows a clear message instead.
"""
import shutil
import subprocess
import threading

from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
    QListWidgetItem, QInputDialog, QLineEdit, QMessageBox, QTimer, Qt, Signal,
)

HAVE_NMCLI = shutil.which("nmcli") is not None


# --- nmcli helpers (no Qt; safe to call from worker threads) ---------------
def _run(args, timeout=20):
    try:
        p = subprocess.run(["nmcli", *args], capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", "nmcli not found"
    except subprocess.TimeoutExpired:
        return 124, "", "operation timed out"
    except Exception as exc:                            # noqa: BLE001
        return 1, "", str(exc)


def _split_terse(line):
    """Split an `nmcli -t` line, honouring its '\\:' / '\\\\' escaping."""
    fields, cur, i = [], [], 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            cur.append(line[i + 1])
            i += 2
            continue
        if c == ":":
            fields.append("".join(cur))
            cur = []
            i += 1
            continue
        cur.append(c)
        i += 1
    fields.append("".join(cur))
    return fields


def _wifi_device():
    rc, out, _ = _run(["-t", "-f", "DEVICE,TYPE,STATE", "device"])
    for line in out.splitlines():
        f = _split_terse(line)
        if len(f) >= 3 and f[1] == "wifi":             # 'wifi', not 'wifi-p2p'
            return f[0], f[2]
    return None, None


def wifi_status():
    s = {"available": HAVE_NMCLI, "radio": False, "state": "", "connectivity": "",
         "ssid": None, "ip": None, "device": None}
    if not HAVE_NMCLI:
        return s

    _, out, _ = _run(["radio", "wifi"])
    s["radio"] = "enabled" in out

    _, out, _ = _run(["-t", "-f", "STATE,CONNECTIVITY", "general"])
    lines = out.strip().splitlines()
    if lines:
        f = _split_terse(lines[0])
        if len(f) >= 2:
            s["state"], s["connectivity"] = f[0], f[1]

    dev, _state = _wifi_device()
    s["device"] = dev
    if dev:
        _, out, _ = _run(["-t", "-f", "ACTIVE,SSID", "dev", "wifi"])
        for line in out.splitlines():
            f = _split_terse(line)
            if len(f) >= 2 and f[0] == "yes":
                s["ssid"] = f[1] or None
                break
        _, out, _ = _run(["-t", "-f", "IP4.ADDRESS", "device", "show", dev])
        for line in out.splitlines():
            f = _split_terse(line)
            if len(f) >= 2 and f[1]:
                s["ip"] = f[1].split("/")[0]
                break
    return s


def wifi_scan():
    rc, out, _ = _run(["-t", "-f", "IN-USE,SIGNAL,SECURITY,SSID", "dev", "wifi", "list"])
    best = {}
    for line in out.splitlines():
        f = _split_terse(line)
        if len(f) < 4:
            continue
        ssid = f[3].strip()
        if not ssid:
            continue                                   # hidden network
        try:
            signal = int(f[1])
        except ValueError:
            signal = 0
        security = f[2].strip() or "Open"
        in_use = f[0].strip() == "*"
        prev = best.get(ssid)
        if prev is None or signal > prev["signal"]:
            best[ssid] = {"ssid": ssid, "signal": signal,
                          "security": security, "in_use": in_use}
        elif in_use:
            best[ssid]["in_use"] = True
    nets = list(best.values())
    nets.sort(key=lambda n: (not n["in_use"], -n["signal"]))
    return nets


def wifi_connect(ssid, password=None):
    args = ["dev", "wifi", "connect", ssid]
    if password:
        args += ["password", password]
    rc, out, err = _run(args, timeout=45)
    msg = (out or err).strip() or ("connected" if rc == 0 else "failed")
    return rc == 0, msg


def wifi_disconnect():
    dev, _ = _wifi_device()
    if not dev:
        return False, "no Wi-Fi device"
    rc, out, err = _run(["dev", "disconnect", dev])
    return rc == 0, (out or err).strip() or ("disconnected" if rc == 0 else "failed")


def wifi_set_radio(on):
    rc, out, err = _run(["radio", "wifi", "on" if on else "off"])
    return rc == 0, (err or out).strip()


def short_status():
    """Compact one-liner for the taskbar indicator."""
    if not HAVE_NMCLI:
        return "No network"
    s = wifi_status()
    if not s["radio"] and not s["ssid"]:
        return "Wi-Fi: off"
    if s["ssid"]:
        return s["ssid"] + ("" if s["connectivity"] == "full" else " (limited)")
    if s["connectivity"] == "full":
        return "Online"
    return "Offline"


# --- the Network app widget ------------------------------------------------
class Network(QWidget):
    _status_ready = Signal(dict)
    _scan_ready = Signal(list)
    _action_ready = Signal(bool, str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.status_label = QLabel("Wi-Fi")
        self.status_label.setWordWrap(True)
        header.addWidget(self.status_label, 1)
        self.radio_btn = QPushButton("Wi-Fi On/Off")
        self.radio_btn.clicked.connect(self._toggle_radio)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.radio_btn)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)

        self.listw = QListWidget()
        self.listw.itemDoubleClicked.connect(lambda _i: self._connect())
        layout.addWidget(self.listw, 1)

        actions = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._connect)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self._disconnect)
        actions.addWidget(self.connect_btn)
        actions.addWidget(self.disconnect_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

        self._status_ready.connect(self._on_status)
        self._scan_ready.connect(self._on_scan)
        self._action_ready.connect(self._on_action)

        if not HAVE_NMCLI:
            self.status_label.setText(
                "NetworkManager (nmcli) is not available, so Wi-Fi can't be "
                "managed here. Your existing connection still works.")
            for b in (self.radio_btn, self.refresh_btn, self.connect_btn, self.disconnect_btn):
                b.setEnabled(False)
            return

        # periodic status refresh
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(8000)
        self.refresh()

    # -- threaded actions ---------------------------------------------------
    def refresh(self):
        self._refresh_status()
        self.status_label.setText("Scanning for networks…")
        threading.Thread(target=lambda: self._scan_ready.emit(wifi_scan()), daemon=True).start()

    def _refresh_status(self):
        threading.Thread(target=lambda: self._status_ready.emit(wifi_status()), daemon=True).start()

    def _on_status(self, s):
        bits = []
        bits.append("Wi-Fi: " + ("on" if s["radio"] else "off"))
        if s["ssid"]:
            bits.append("connected to " + s["ssid"])
        if s["connectivity"]:
            bits.append("internet: " + s["connectivity"])
        if s["ip"]:
            bits.append("IP " + s["ip"])
        self.status_label.setText("   ·   ".join(bits))

    def _on_scan(self, nets):
        self.listw.clear()
        for n in nets:
            mark = "✓ " if n["in_use"] else "   "
            lock = "secured" if n["security"] not in ("", "Open", "--") else "open"
            item = QListWidgetItem(f"{mark}{n['ssid']}    {n['signal']}%   {lock}")
            item.setData(Qt.UserRole, (n["ssid"], n["security"]))
            self.listw.addItem(item)
        if not nets:
            self.listw.addItem(QListWidgetItem("(no networks found)"))

    def _selected(self):
        item = self.listw.currentItem()
        if item is None:
            return None
        data = item.data(Qt.UserRole)
        return data            # (ssid, security) or None for the placeholder

    def _connect(self):
        data = self._selected()
        if not data:
            return
        ssid, security = data
        password = None
        if security not in ("", "Open", "--"):
            password, ok = QInputDialog.getText(
                self, "Wi-Fi password",
                f"Password for '{ssid}'\n(leave blank if it's already saved):",
                QLineEdit.Password)
            if not ok:
                return
            password = password or None
        self._busy(f"Connecting to {ssid}…")
        threading.Thread(
            target=lambda: self._action_ready.emit(*wifi_connect(ssid, password)),
            daemon=True).start()

    def _disconnect(self):
        self._busy("Disconnecting…")
        threading.Thread(
            target=lambda: self._action_ready.emit(*wifi_disconnect()),
            daemon=True).start()

    def _toggle_radio(self):
        def work():
            on = wifi_status()["radio"]
            ok, msg = wifi_set_radio(not on)
            self._action_ready.emit(ok, msg or ("Wi-Fi turned " + ("off" if on else "on")))
        self._busy("Toggling Wi-Fi…")
        threading.Thread(target=work, daemon=True).start()

    def _on_action(self, ok, msg):
        if not ok:
            QMessageBox.warning(self, "Network", msg or "Action failed")
        self.refresh()

    def _busy(self, text):
        self.status_label.setText(text)
