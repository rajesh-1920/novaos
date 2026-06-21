# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Network - a SANDBOXED Wi-Fi manager for NovaOS Desktop.

Important: this manages a *virtual* network that belongs to NovaOS Desktop only.
Turning Wi-Fi off / connecting / disconnecting here changes an in-memory state
inside the app and gates NovaOS apps (e.g. the Browser goes offline) — it does
**not** touch your computer's real Wi-Fi radio or connection.

For a realistic network list it performs a *read-only* scan via nmcli (which
never changes host state); if nmcli is unavailable it shows a few demo networks.
When NovaOS is "online", the Browser uses your computer's real internet.
"""
import shutil
import subprocess
import threading

from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget,
    QListWidgetItem, Qt, Signal,
)

HAVE_NMCLI = shutil.which("nmcli") is not None

DEMO_NETWORKS = [
    {"ssid": "NovaNet", "signal": 92, "security": "WPA2"},
    {"ssid": "NovaNet-5G", "signal": 78, "security": "WPA2"},
    {"ssid": "CoffeeShop", "signal": 54, "security": "Open"},
    {"ssid": "Guest", "signal": 38, "security": "Open"},
]


# --- read-only host helpers (never change host state) -----------------------
def _run(args, timeout=15):
    try:
        p = subprocess.run(["nmcli", *args], capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception:                                   # noqa: BLE001
        return 1, "", "nmcli error"


def _split_terse(line):
    fields, cur, i = [], [], 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            cur.append(line[i + 1]); i += 2; continue
        if c == ":":
            fields.append("".join(cur)); cur = []; i += 1; continue
        cur.append(c); i += 1
    fields.append("".join(cur))
    return fields


def real_current_ssid():
    """Read (only) the host's currently-connected Wi-Fi SSID, if any."""
    if not HAVE_NMCLI:
        return None
    _, out, _ = _run(["-t", "-f", "ACTIVE,SSID", "dev", "wifi"])
    for line in out.splitlines():
        f = _split_terse(line)
        if len(f) >= 2 and f[0] == "yes" and f[1]:
            return f[1]
    return None


def scan_networks():
    """Read-only list of nearby Wi-Fi networks (demo list if nmcli is absent)."""
    if not HAVE_NMCLI:
        return list(DEMO_NETWORKS)
    _, out, _ = _run(["-t", "-f", "SIGNAL,SECURITY,SSID", "dev", "wifi", "list"])
    best = {}
    for line in out.splitlines():
        f = _split_terse(line)
        if len(f) < 3:
            continue
        ssid = f[2].strip()
        if not ssid:
            continue
        try:
            signal = int(f[0])
        except ValueError:
            signal = 0
        security = f[1].strip() or "Open"
        if ssid not in best or signal > best[ssid]["signal"]:
            best[ssid] = {"ssid": ssid, "signal": signal, "security": security}
    nets = list(best.values()) or list(DEMO_NETWORKS)
    nets.sort(key=lambda n: -n["signal"])
    return nets


# --- virtual NovaOS network state (in-memory; affects NovaOS apps only) -----
_state = {"wifi_on": True, "ssid": None, "online": False}
_initialized = False


def _ensure_init():
    global _initialized
    if _initialized:
        return
    _initialized = True
    # Default the virtual connection to mirror the host's current SSID (display
    # only), so NovaOS starts "online" and the Browser works out of the box.
    _state["ssid"] = real_current_ssid() or "NovaNet"
    _state["wifi_on"] = True
    _state["online"] = True


def state():
    _ensure_init()
    return dict(_state)


def is_online():
    """Whether NovaOS Desktop considers itself connected (gates the Browser)."""
    _ensure_init()
    return _state["wifi_on"] and _state["online"] and bool(_state["ssid"])


def set_wifi_on(on):
    _ensure_init()
    _state["wifi_on"] = bool(on)
    _state["online"] = bool(on and _state["ssid"])
    return True


def vconnect(ssid):
    _ensure_init()
    _state["wifi_on"] = True
    _state["ssid"] = ssid
    _state["online"] = True
    return True


def vdisconnect():
    _ensure_init()
    _state["online"] = False
    return True


def short_status():
    """Compact taskbar string, reflecting the VIRTUAL NovaOS state."""
    s = state()
    if not s["wifi_on"]:
        return "Wi-Fi: off"
    if s["online"] and s["ssid"]:
        return s["ssid"]
    return "Offline"


# --- the Network app widget ------------------------------------------------
class Network(QWidget):
    _scan_ready = Signal(list)

    def __init__(self):
        super().__init__()
        self._nets = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        note = QLabel("Sandboxed: this only affects NovaOS Desktop — "
                      "your computer's real Wi-Fi is never changed.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#8a93a8; font-size:11px;")
        layout.addWidget(note)

        controls = QHBoxLayout()
        self.radio_btn = QPushButton()
        self.radio_btn.clicked.connect(self._toggle_radio)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._rescan)
        controls.addWidget(self.radio_btn)
        controls.addWidget(self.refresh_btn)
        controls.addStretch(1)
        layout.addLayout(controls)

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

        self._scan_ready.connect(self._on_scan)
        self._render_status()
        self._rescan()

    # -- status / list ------------------------------------------------------
    def _render_status(self):
        s = state()
        if not s["wifi_on"]:
            self.status_label.setText("NovaOS Wi-Fi: off")
        elif s["online"] and s["ssid"]:
            self.status_label.setText(
                f"NovaOS Wi-Fi: on   ·   connected to {s['ssid']}   ·   online")
        else:
            self.status_label.setText("NovaOS Wi-Fi: on   ·   not connected")
        self.radio_btn.setText("Turn Wi-Fi Off" if s["wifi_on"] else "Turn Wi-Fi On")

    def _rescan(self):
        self.status_label.setText("Scanning for networks…")
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        nets = scan_networks()
        try:
            self._scan_ready.emit(nets)
        except RuntimeError:
            pass                       # the Network window was closed mid-scan

    def _on_scan(self, nets):
        self._nets = nets
        self._show_list()
        self._render_status()

    def _show_list(self):
        s = state()
        connected = s["ssid"] if (s["wifi_on"] and s["online"]) else None
        self.listw.clear()
        for n in self._nets:
            mark = "✓ " if n["ssid"] == connected else "   "
            lock = "open" if n["security"] in ("", "Open", "--") else "secured"
            item = QListWidgetItem(f"{mark}{n['ssid']}    {n['signal']}%   {lock}")
            item.setData(Qt.UserRole, n["ssid"])
            self.listw.addItem(item)
        if not self._nets:
            self.listw.addItem(QListWidgetItem("(no networks found)"))

    # -- virtual actions (no host changes) ----------------------------------
    def _connect(self):
        item = self.listw.currentItem()
        if item is None:
            return
        ssid = item.data(Qt.UserRole)
        if ssid:
            vconnect(ssid)
            self._render_status()
            self._show_list()

    def _disconnect(self):
        vdisconnect()
        self._render_status()
        self._show_list()

    def _toggle_radio(self):
        set_wifi_on(not state()["wifi_on"])
        self._render_status()
        self._show_list()
