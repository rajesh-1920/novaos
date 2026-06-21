# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Monitor - a task manager / system monitor for NovaOS Desktop.

Shows live system CPU and memory usage plus a sortable table of running
processes (PID, name, CPU%, memory, user). Data is gathered on a background
thread (the UI never freezes) using psutil when available, otherwise `ps`.

"End Task" is deliberately conservative: it only terminates *your own*
processes, never PID 1, and always asks for confirmation — so the simulated
desktop can't accidentally take down system services.
"""
import getpass
import os
import signal
import subprocess
import threading

from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QTimer, Qt, Signal,
)

try:
    import psutil
    HAVE_PSUTIL = True
except Exception:
    HAVE_PSUTIL = False

CURRENT_USER = getpass.getuser()
COLUMNS = ["PID", "Name", "CPU %", "Mem (MB)", "User"]


# --- data gathering (no Qt; safe on a worker thread) -----------------------
def _gather_psutil():
    cpu = psutil.cpu_percent(None)            # since the previous call
    vm = psutil.virtual_memory()
    procs = []
    for p in psutil.process_iter(["pid", "ppid", "name", "username",
                                  "memory_info", "cpu_percent"]):
        info = p.info
        mi = info.get("memory_info")
        procs.append({
            "pid": info["pid"],
            "name": info.get("name") or "?",
            "user": (info.get("username") or "?").split("\\")[-1],
            "cpu": float(info.get("cpu_percent") or 0.0),
            "mem": (mi.rss / (1024 * 1024)) if mi else 0.0,
        })
    return cpu, vm.used / 1e9, vm.total / 1e9, vm.percent, procs


def _meminfo_kb():
    total = avail = 0
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    avail = int(line.split()[1])
    except OSError:
        pass
    return total, avail


def _gather_ps():
    out = subprocess.run(
        ["ps", "-eo", "pid,user:32,pcpu,pmem,comm", "--sort=-pcpu"],
        capture_output=True, text=True, timeout=10).stdout
    total_kb, avail_kb = _meminfo_kb()
    total_mb = total_kb / 1024.0
    procs, total_cpu = [], 0.0
    for line in out.splitlines()[1:]:
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        pid, user, pcpu, pmem, comm = parts
        try:
            cpu = float(pcpu)
            mem_mb = float(pmem) / 100.0 * total_mb
        except ValueError:
            continue
        total_cpu += cpu
        procs.append({"pid": int(pid), "name": comm, "user": user,
                      "cpu": cpu, "mem": mem_mb})
    ncpu = os.cpu_count() or 1
    used_mb = (total_kb - avail_kb) / 1024.0
    mem_pct = (used_mb / total_mb * 100.0) if total_mb else 0.0
    return min(total_cpu / ncpu, 100.0), used_mb / 1000.0, total_mb / 1000.0, mem_pct, procs


def gather():
    return _gather_psutil() if HAVE_PSUTIL else _gather_ps()


def end_task(pid):
    if HAVE_PSUTIL:
        psutil.Process(pid).terminate()
    else:
        os.kill(pid, signal.SIGTERM)


# --- a table item that sorts numerically -----------------------------------
class _NumItem(QTableWidgetItem):
    def __init__(self, value, text):
        super().__init__(text)
        self.value = value
        self.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def __lt__(self, other):
        try:
            return self.value < other.value
        except (AttributeError, TypeError):
            return super().__lt__(other)


class Monitor(QWidget):
    _data_ready = Signal(object)

    def __init__(self):
        super().__init__()
        self._sort_col = 2          # CPU %
        self._sort_order = Qt.DescendingOrder

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.summary = QLabel("Collecting…")
        f = self.summary.font()
        f.setPointSize(11)
        self.summary.setFont(f)
        layout.addWidget(self.summary)

        controls = QHBoxLayout()
        self.end_btn = QPushButton("End Task")
        self.end_btn.clicked.connect(self._end_task)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        controls.addWidget(self.end_btn)
        controls.addWidget(self.refresh_btn)
        controls.addStretch(1)
        engine = "psutil" if HAVE_PSUTIL else "ps"
        controls.addWidget(QLabel(f"source: {engine}"))
        layout.addLayout(controls)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(self._sort_col, self._sort_order)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)        # Name column
        hdr.sortIndicatorChanged.connect(self._remember_sort)
        layout.addWidget(self.table, 1)

        note = QLabel("End Task only affects your own processes (with "
                      "confirmation) — system services are protected.")
        note.setStyleSheet("color:#8a93a8; font-size:11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._data_ready.connect(self._on_data)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(2000)
        self.refresh()

    # -- refresh ------------------------------------------------------------
    def refresh(self):
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            data = gather()
        except Exception as exc:                # noqa: BLE001
            data = ("error", str(exc))
        try:
            self._data_ready.emit(data)
        except RuntimeError:
            pass                                # window closed mid-refresh

    def _remember_sort(self, col, order):
        self._sort_col, self._sort_order = col, order

    def _on_data(self, data):
        if data and data[0] == "error":
            self.summary.setText(f"Error: {data[1]}")
            return
        cpu, used_gb, total_gb, mem_pct, procs = data
        self.summary.setText(
            f"CPU: {cpu:.0f}%      "
            f"Memory: {used_gb:.1f} / {total_gb:.1f} GB ({mem_pct:.0f}%)      "
            f"Processes: {len(procs)}")

        selected_pid = self._selected_pid()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(procs))
        for row, p in enumerate(procs):
            pid_item = _NumItem(p["pid"], str(p["pid"]))
            name_item = QTableWidgetItem(" " + p["name"])
            cpu_item = _NumItem(p["cpu"], f"{p['cpu']:.1f}")
            mem_item = _NumItem(p["mem"], f"{p['mem']:.1f}")
            user_item = QTableWidgetItem(p["user"])
            pid_item.setData(Qt.UserRole, (p["pid"], p["user"]))
            self.table.setItem(row, 0, pid_item)
            self.table.setItem(row, 1, name_item)
            self.table.setItem(row, 2, cpu_item)
            self.table.setItem(row, 3, mem_item)
            self.table.setItem(row, 4, user_item)
        self.table.setSortingEnabled(True)
        self.table.sortItems(self._sort_col, self._sort_order)
        if selected_pid is not None:
            self._reselect(selected_pid)

    # -- selection helpers --------------------------------------------------
    def _selected_pid(self):
        items = self.table.selectedItems()
        if not items:
            return None
        data = self.table.item(items[0].row(), 0).data(Qt.UserRole)
        return data[0] if data else None

    def _reselect(self, pid):
        for row in range(self.table.rowCount()):
            data = self.table.item(row, 0).data(Qt.UserRole)
            if data and data[0] == pid:
                self.table.selectRow(row)
                return

    # -- end task -----------------------------------------------------------
    def _end_task(self):
        items = self.table.selectedItems()
        if not items:
            return
        data = self.table.item(items[0].row(), 0).data(Qt.UserRole)
        if not data:
            return
        pid, user = data
        name = self.table.item(items[0].row(), 1).text().strip()

        if pid == 1:
            QMessageBox.warning(self, "End Task", "Refusing to end PID 1 (init).")
            return
        if user != CURRENT_USER:
            QMessageBox.warning(
                self, "End Task",
                f"'{name}' (PID {pid}) belongs to '{user}'.\n"
                f"You can only end your own ({CURRENT_USER}) processes.")
            return
        if QMessageBox.question(
                self, "End Task",
                f"End '{name}' (PID {pid})?") != QMessageBox.Yes:
            return
        try:
            end_task(pid)
        except Exception as exc:                # noqa: BLE001
            QMessageBox.warning(self, "End Task", f"Could not end task: {exc}")
        self.refresh()
