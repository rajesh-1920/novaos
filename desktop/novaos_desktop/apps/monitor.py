# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Monitor - the task manager for NovaOS Desktop.

This is fully sandboxed: it lists only the apps running *inside NovaOS Desktop*
(the open windows), never the host machine's processes. Each NovaOS app gets a
NovaOS PID, a status and an uptime; "End Task" simply closes that app's window.

The header shows NovaOS Desktop's own footprint (its CPU%/RAM via psutil, if
available) — i.e. the OS project's usage, not other programs on the computer.
"""
import os
import time

from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox, QTimer, Qt,
)

try:
    import psutil
    _SELF = psutil.Process(os.getpid())
    HAVE_PSUTIL = True
except Exception:
    HAVE_PSUTIL = False

COLUMNS = ["PID", "App", "Status", "Uptime"]


def _fmt_uptime(secs):
    s = int(secs)
    if s < 60:
        return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


class _NumItem(QTableWidgetItem):
    def __init__(self, value, text):
        super().__init__(text)
        self.value = value

    def __lt__(self, other):
        try:
            return self.value < other.value
        except (AttributeError, TypeError):
            return super().__lt__(other)


class Monitor(QWidget):
    def __init__(self, desktop):
        super().__init__()
        self.desktop = desktop

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.summary = QLabel("NovaOS Desktop")
        f = self.summary.font()
        f.setPointSize(11)
        self.summary.setFont(f)
        layout.addWidget(self.summary)

        controls = QHBoxLayout()
        self.end_btn = QPushButton("End Task")
        self.end_btn.clicked.connect(self._end_task)
        self.focus_btn = QPushButton("Switch To")
        self.focus_btn.clicked.connect(self._switch_to)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        for b in (self.end_btn, self.focus_btn, self.refresh_btn):
            controls.addWidget(b)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.itemDoubleClicked.connect(lambda _i: self._switch_to())
        layout.addWidget(self.table, 1)

        note = QLabel("Shows only NovaOS Desktop apps — your computer's other "
                      "programs are not listed. End Task closes the app.")
        note.setStyleSheet("color:#8a93a8; font-size:11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        if HAVE_PSUTIL:
            _SELF.cpu_percent(None)          # prime CPU measurement

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(1000)
        # Defer the first refresh so this window is already registered as a
        # running app (it is recorded just after launch_app creates it).
        QTimer.singleShot(0, self.refresh)

    # -- refresh ------------------------------------------------------------
    def refresh(self):
        apps = self.desktop.running_apps()

        if HAVE_PSUTIL:
            cpu = _SELF.cpu_percent(None)
            ram = _SELF.memory_info().rss / (1024 * 1024)
            self.summary.setText(
                f"NovaOS Desktop    ·    CPU {cpu:.0f}%    ·    "
                f"RAM {ram:.0f} MB    ·    {len(apps)} app(s) running")
        else:
            self.summary.setText(f"NovaOS Desktop    ·    {len(apps)} app(s) running")

        selected = self._selected_pid()
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(apps))
        for row, a in enumerate(apps):
            pid_item = _NumItem(a["pid"], str(a["pid"]))
            pid_item.setData(Qt.UserRole, a["pid"])
            self.table.setItem(row, 0, pid_item)
            self.table.setItem(row, 1, QTableWidgetItem(" " + a["name"]))
            self.table.setItem(row, 2, QTableWidgetItem(a["status"]))
            self.table.setItem(row, 3, _NumItem(a["uptime"], _fmt_uptime(a["uptime"])))
        self.table.setSortingEnabled(True)
        if selected is not None:
            self._reselect(selected)

    # -- selection ----------------------------------------------------------
    def _selected_pid(self):
        items = self.table.selectedItems()
        if not items:
            return None
        item = self.table.item(items[0].row(), 0)
        return item.data(Qt.UserRole) if item else None

    def _selected_name(self):
        items = self.table.selectedItems()
        if not items:
            return ""
        item = self.table.item(items[0].row(), 1)
        return item.text().strip() if item else ""

    def _reselect(self, pid):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == pid:
                self.table.selectRow(row)
                return

    # -- actions ------------------------------------------------------------
    def _switch_to(self):
        pid = self._selected_pid()
        if pid is not None:
            self.desktop.focus_app(pid)

    def _end_task(self):
        pid = self._selected_pid()
        if pid is None:
            return
        name = self._selected_name()
        if QMessageBox.question(self, "End Task",
                                f"Close '{name}' (PID {pid})?") == QMessageBox.Yes:
            self.desktop.close_app(pid)
            self.refresh()
