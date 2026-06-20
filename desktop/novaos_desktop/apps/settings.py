# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Settings - change wallpaper, theme, and username."""
from ..qt import (
    QWidget, QFormLayout, QComboBox, QLineEdit, QLabel, QVBoxLayout, QPushButton,
)

from ..style import WALLPAPERS


class Settings(QWidget):
    def __init__(self, desktop):
        super().__init__()
        self.desktop = desktop

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        title = QLabel("System Settings")
        f = title.font()
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)
        outer.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)

        self.wallpaper = QComboBox()
        self.wallpaper.addItems(list(WALLPAPERS.keys()))
        self.wallpaper.setCurrentText(desktop.wallpaper_name)
        self.wallpaper.currentTextChanged.connect(desktop.set_wallpaper)
        form.addRow("Wallpaper", self.wallpaper)

        self.theme = QComboBox()
        self.theme.addItems(["dark", "light"])
        self.theme.setCurrentText(desktop.theme_name)
        self.theme.currentTextChanged.connect(desktop.set_theme)
        form.addRow("Theme", self.theme)

        self.username = QLineEdit(desktop.username)
        self.username.textChanged.connect(desktop.set_username)
        form.addRow("Username", self.username)

        outer.addLayout(form)

        info = QLabel(
            "NovaOS Desktop\n"
            "A simulated operating-system desktop built with PySide6,\n"
            "companion to the NovaOS kernel."
        )
        info.setWordWrap(True)
        outer.addWidget(info)
        outer.addStretch(1)
