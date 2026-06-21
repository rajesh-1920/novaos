# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""NovaDesktop - the main window that ties the simulated desktop together.

It provides the wallpaper (an MDI area), a bottom taskbar with a Start menu,
running-window buttons and a live clock, a column of desktop icons, and the
window-management glue that launches apps into draggable MDI subwindows.
"""
import time
from datetime import datetime

from .qt import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMdiArea, QFrame,
    QPushButton, QToolButton, QLabel, QMenu, QApplication,
    Qt, QTimer, QSize, QPoint, Signal, QShortcut, QKeySequence,
)

from .icons import make_icon
from .style import theme_qss, wallpaper_brush, WALLPAPERS
from .window import AppWindow
from .apps.terminal import Terminal
from .apps.files import Files
from .apps.editor import Editor
from .apps.browser import Browser
from .apps.network import Network, short_status
from .apps.monitor import Monitor
from .apps.camera import Camera
from .apps.viewer import ImageViewer, is_image
from .apps.calculator import Calculator
from .apps.settings import Settings
from .apps.about import About
from . import __version__

# name -> (icon letter, color)
APP_SPECS = {
    "Terminal":   ("T", "#2d7d46"),
    "Files":      ("F", "#3b6ea5"),
    "Browser":    ("B", "#2563eb"),
    "Network":    ("N", "#0d9488"),
    "Monitor":    ("M", "#e11d48"),
    "Camera":     ("◉", "#db2777"),
    "Viewer":     ("V", "#d97706"),
    "Editor":     ("E", "#8a5cf6"),
    "Calculator": ("C", "#c2410c"),
    "Settings":   ("S", "#475569"),
    "About":      ("i", "#0891b2"),
}

DEFAULT_SIZES = {
    "Terminal":   QSize(660, 430),
    "Files":      QSize(560, 430),
    "Browser":    QSize(860, 580),
    "Network":    QSize(540, 480),
    "Monitor":    QSize(700, 480),
    "Camera":     QSize(640, 560),
    "Viewer":     QSize(700, 560),
    "Editor":     QSize(640, 470),
    "Calculator": QSize(300, 430),
    "Settings":   QSize(440, 380),
    "About":      QSize(480, 440),
}


class NovaDesktop(QMainWindow):
    _net_status = Signal(str)

    def __init__(self, fs):
        super().__init__()
        self.fs = fs
        self.username = "nova"
        self.theme_name = "dark"
        self.wallpaper_name = "Midnight"
        self._cascade = 0
        self._taskbar_buttons = {}        # AppWindow -> QPushButton
        self._app_info = {}               # AppWindow -> {pid, name, started}
        self._next_pid = 1                # NovaOS process ids (sandboxed)

        self.setWindowTitle("NovaOS Desktop")
        self.setWindowIcon(make_icon("N", "#3b6ea5"))
        self.resize(1100, 720)

        # Desktop surface (wallpaper + app windows).
        self.mdi = QMdiArea()
        self.mdi.setBackground(wallpaper_brush(self.wallpaper_name))
        self.mdi.setOption(QMdiArea.DontMaximizeSubWindowOnActivation, True)
        self.mdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mdi.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.mdi, 1)
        layout.addWidget(self._build_taskbar())
        self.setCentralWidget(central)

        self._build_desktop_icons()

        # Live clock.
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()

        # Live network/Wi-Fi indicator (polled off the GUI thread).
        self._net_status.connect(self.net_btn.setText)
        self._net_timer = QTimer(self)
        self._net_timer.timeout.connect(self._poll_net)
        self._net_timer.start(2000)
        self._poll_net()

        QApplication.instance().setStyleSheet(theme_qss(self.theme_name))

        # Global shortcuts.
        close_sc = QShortcut(QKeySequence("Ctrl+W"), self)
        close_sc.activated.connect(self._close_active)
        quit_sc = QShortcut(QKeySequence("Ctrl+Q"), self)
        quit_sc.activated.connect(self.close)

    # -- taskbar ------------------------------------------------------------
    def _build_taskbar(self):
        bar = QFrame()
        bar.setObjectName("Taskbar")
        bar.setFixedHeight(46)
        row = QHBoxLayout(bar)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(8)

        self.start_btn = QPushButton("  Start  ")
        self.start_btn.setObjectName("StartButton")
        self.start_btn.clicked.connect(self._show_start_menu)
        row.addWidget(self.start_btn)

        self._running = QHBoxLayout()
        self._running.setSpacing(6)
        running_container = QWidget()
        running_container.setLayout(self._running)
        row.addWidget(running_container, 1)

        self.net_btn = QPushButton("Wi-Fi")
        self.net_btn.setObjectName("NetButton")
        self.net_btn.setToolTip("Network — click to manage Wi-Fi")
        self.net_btn.clicked.connect(lambda: self.launch_app("Network"))
        row.addWidget(self.net_btn)

        self.clock = QLabel()
        self.clock.setObjectName("Clock")
        self.clock.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.clock)
        return bar

    def _show_start_menu(self):
        menu = QMenu(self)
        for name, (letter, color) in APP_SPECS.items():
            act = menu.addAction(make_icon(letter, color), name)
            act.triggered.connect(lambda _=False, n=name: self.launch_app(n))
        menu.addSeparator()
        quit_act = menu.addAction("Power off")
        quit_act.triggered.connect(self.close)
        # pop up just above the Start button
        pos = self.start_btn.mapToGlobal(QPoint(0, 0))
        menu.popup(QPoint(pos.x(), pos.y() - menu.sizeHint().height()))

    def _close_active(self):
        sub = self.mdi.activeSubWindow()
        if sub is not None:
            sub.close()

    def _tick_clock(self):
        self.clock.setText(datetime.now().strftime("%a %d %b   %H:%M:%S"))

    def _poll_net(self):
        # Virtual state -> instant; no subprocess, safe to read on the GUI thread.
        self._net_status.emit(short_status())

    # -- desktop icons ------------------------------------------------------
    def _build_desktop_icons(self):
        self.icons = QWidget(self.mdi.viewport())
        self.icons.setObjectName("DesktopIcons")
        col = QVBoxLayout(self.icons)
        col.setContentsMargins(10, 12, 10, 12)
        col.setSpacing(14)
        for name in ("Terminal", "Files", "Browser", "Network", "Monitor", "Editor", "About"):
            letter, color = APP_SPECS[name]
            btn = QToolButton()
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setIcon(make_icon(letter, color))
            btn.setIconSize(QSize(44, 44))
            btn.setText(name)
            btn.setFixedWidth(96)                 # room for the full label
            btn.setStyleSheet(
                "QToolButton { color: white; background: transparent; border: none;"
                " padding: 4px; }"
                "QToolButton:hover { background: rgba(255,255,255,0.14); border-radius: 8px; }"
            )
            btn.clicked.connect(lambda _=False, n=name: self.launch_app(n))
            col.addWidget(btn, 0, Qt.AlignHCenter)
        self.icons.move(8, 8)
        # Size the panel to its content so each button keeps its full height and
        # the label under the icon is never clipped.
        self.icons.resize(self.icons.sizeHint())
        self.icons.show()
        self.icons.raise_()

    # -- app launching ------------------------------------------------------
    def _create_widget(self, name, path=None):
        if name == "Terminal":
            return Terminal(self.fs, self.launch_app, self.system_info,
                            lambda: self.username)
        if name == "Files":
            return Files(self.fs, self._open_path)
        if name == "Browser":
            return Browser()
        if name == "Network":
            return Network()
        if name == "Monitor":
            return Monitor(self)
        if name == "Camera":
            return Camera(self.fs)
        if name == "Viewer":
            w = ImageViewer(self.fs)
            if path:
                w.open_path(path)
            return w
        if name == "Editor":
            w = Editor(self.fs)
            if path:
                w.open_path(path)
            return w
        if name == "Calculator":
            return Calculator()
        if name == "Settings":
            return Settings(self)
        if name == "About":
            return About()
        return None

    def _open_path(self, path):
        """Open a drive file in the right app: images -> Viewer, else Editor."""
        if is_image(path):
            self.launch_app("Viewer", path=path)
        else:
            self.launch_app("Editor", path=path)

    def launch_app(self, name, path=None):
        if name not in APP_SPECS:
            return None
        widget = self._create_widget(name, path)
        if widget is None:
            return None

        sub = AppWindow(self.mdi)
        sub.setWidget(widget)
        sub.setWindowTitle(name)
        sub.setWindowIcon(make_icon(*APP_SPECS[name]))
        sub.setAttribute(Qt.WA_DeleteOnClose, True)
        sub.closed.connect(self._on_window_closed)
        self.mdi.addSubWindow(sub)
        sub.resize(DEFAULT_SIZES.get(name, QSize(560, 420)))

        offset = 28 + (self._cascade % 6) * 26
        sub.move(120 + offset, 20 + (self._cascade % 6) * 26)
        self._cascade += 1

        sub.show()
        self.mdi.setActiveSubWindow(sub)
        self._add_taskbar_button(sub, name)
        self._app_info[sub] = {"pid": self._next_pid, "name": name,
                               "started": time.monotonic()}
        self._next_pid += 1
        return widget

    def _add_taskbar_button(self, sub, name):
        btn = QPushButton(name)
        btn.setIcon(make_icon(*APP_SPECS[name]))
        btn.setCheckable(True)
        btn.setChecked(True)
        btn.clicked.connect(lambda _=False, s=sub: self._focus_window(s))
        self._running.addWidget(btn)
        self._taskbar_buttons[sub] = btn

    def _focus_window(self, sub):
        if sub.isMinimized():
            sub.showNormal()
        self.mdi.setActiveSubWindow(sub)
        sub.widget().setFocus()

    def _on_window_closed(self, sub):
        btn = self._taskbar_buttons.pop(sub, None)
        if btn is not None:
            self._running.removeWidget(btn)
            btn.deleteLater()
        self._app_info.pop(sub, None)

    # -- NovaOS "process" table (used by the Monitor app) -------------------
    def running_apps(self):
        """List the apps running inside NovaOS Desktop (not host processes)."""
        now = time.monotonic()
        active = self.mdi.activeSubWindow()
        apps = []
        for sub, info in self._app_info.items():
            if sub.isMinimized():
                status = "minimized"
            elif sub is active:
                status = "active"
            else:
                status = "running"
            apps.append({"pid": info["pid"], "name": info["name"],
                         "status": status, "uptime": now - info["started"]})
        apps.sort(key=lambda a: a["pid"])
        return apps

    def focus_app(self, pid):
        for sub, info in self._app_info.items():
            if info["pid"] == pid:
                if sub.isMinimized():
                    sub.showNormal()
                self.mdi.setActiveSubWindow(sub)
                sub.widget().setFocus()
                return True
        return False

    def close_app(self, pid):
        for sub, info in list(self._app_info.items()):
            if info["pid"] == pid:
                sub.close()
                return True
        return False

    # -- settings hooks -----------------------------------------------------
    def set_wallpaper(self, name):
        self.wallpaper_name = name
        self.mdi.setBackground(wallpaper_brush(name))
        self.mdi.update()

    def set_theme(self, name):
        self.theme_name = name
        QApplication.instance().setStyleSheet(theme_qss(name))

    def set_username(self, name):
        self.username = name.strip() or "nova"

    def system_info(self):
        return {
            "os": "NovaOS Desktop",
            "version": __version__,
            "theme": self.theme_name,
            "wallpaper": self.wallpaper_name,
            "apps": list(APP_SPECS.keys()),
        }
