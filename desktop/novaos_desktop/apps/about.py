# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""About - information about NovaOS Desktop."""
from ..qt import QWidget, QVBoxLayout, QLabel, Qt

from .. import __version__
from ..icons import make_pixmap

LOGO = r"""
    _   __                 ____  _____
   / | / /___ _   ______ _/ __ \/ ___/
  /  |/ / __ \ | / / __ `/ / / /\__ \
 / /|  / /_/ / |/ / /_/ / /_/ /___/ /
/_/ |_/\____/|___/\__,_/\____//____/
"""


class About(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignTop)

        icon = QLabel()
        icon.setPixmap(make_pixmap("N", "#3b6ea5", 72))
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        name = QLabel("NovaOS Desktop")
        nf = name.font()
        nf.setPointSize(18)
        nf.setBold(True)
        name.setFont(nf)
        name.setAlignment(Qt.AlignCenter)
        layout.addWidget(name)

        ver = QLabel(f"version {__version__}")
        ver.setAlignment(Qt.AlignCenter)
        layout.addWidget(ver)

        desc = QLabel(
            "A simulated operating-system desktop, built with Python + PySide6.\n"
            "It is a companion to the NovaOS bare-metal kernel: this app mimics\n"
            "an OS desktop (windows, taskbar, start menu, apps) as a normal\n"
            "desktop program.\n\n"
            "Built-in apps: Terminal, Files, Browser, Editor, Calculator,\n"
            "Settings, About.\n\n"
            "License: MIT"
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
