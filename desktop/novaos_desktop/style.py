# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Themes: Qt style sheets and desktop wallpaper brushes."""
from .qt import QLinearGradient, QGradient, QBrush, QColor

# Wallpaper presets: name -> (top color, bottom color)
WALLPAPERS = {
    "Midnight": ("#1a1b26", "#24283b"),
    "Ocean":    ("#0b3d5c", "#1f6f8b"),
    "Sunset":   ("#3b1f47", "#c2410c"),
    "Forest":   ("#0f2417", "#2d7d46"),
    "Slate":    ("#0f172a", "#334155"),
}


def wallpaper_brush(name: str) -> QBrush:
    top, bottom = WALLPAPERS.get(name, WALLPAPERS["Midnight"])
    grad = QLinearGradient(0, 0, 0, 1)
    grad.setCoordinateMode(QGradient.ObjectBoundingMode)
    grad.setColorAt(0.0, QColor(top))
    grad.setColorAt(1.0, QColor(bottom))
    return QBrush(grad)


# Dark UI theme (default).
QSS_DARK = """
* { font-family: 'Sans Serif'; font-size: 13px; color: #e5e9f0; }
QMainWindow, QWidget { background: transparent; }

QPlainTextEdit, QTextEdit, QListWidget, QLineEdit, QTreeView {
    background: #1e2230; color: #e5e9f0;
    border: 1px solid #323a52; border-radius: 6px;
    selection-background-color: #3b6ea5; selection-color: white;
}
QPlainTextEdit, QTextEdit { font-family: 'Monospace'; }

QPushButton, QToolButton {
    background: #2a3145; color: #e5e9f0;
    border: 1px solid #3a425e; border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover, QToolButton:hover { background: #38415c; }
QPushButton:pressed, QToolButton:pressed { background: #455a82; }

QLabel { background: transparent; }

QMenu { background: #232838; border: 1px solid #3a425e; padding: 6px; }
QMenu::item { padding: 8px 28px 8px 12px; border-radius: 6px; }
QMenu::item:selected { background: #3b6ea5; }

QComboBox { background: #2a3145; border: 1px solid #3a425e; border-radius: 6px; padding: 4px 8px; }
QComboBox QAbstractItemView { background: #232838; selection-background-color: #3b6ea5; }

QScrollBar:vertical { background: transparent; width: 12px; }
QScrollBar::handle:vertical { background: #3a425e; border-radius: 6px; min-height: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }

#Taskbar { background: #11151f; border-top: 1px solid #2a3145; }
#StartButton { background: #3b6ea5; color: white; font-weight: bold; border: none; border-radius: 6px; }
#StartButton:hover { background: #4a82c0; }
#Clock { color: #c0caf5; padding-right: 8px; }
#NetButton { background: transparent; border: none; color: #c0caf5; padding: 4px 10px; }
#NetButton:hover { background: #1c2233; border-radius: 6px; }
#DesktopIcons { background: transparent; }
QMdiSubWindow { background: #1e2230; }
QMdiSubWindow > QWidget { background: #1e2230; }
"""

# A lighter theme.
QSS_LIGHT = """
* { font-family: 'Sans Serif'; font-size: 13px; color: #1e2230; }
QMainWindow, QWidget { background: transparent; }

QPlainTextEdit, QTextEdit, QListWidget, QLineEdit, QTreeView {
    background: #ffffff; color: #1e2230;
    border: 1px solid #c7d0e0; border-radius: 6px;
    selection-background-color: #3b6ea5; selection-color: white;
}
QPlainTextEdit, QTextEdit { font-family: 'Monospace'; }

QPushButton, QToolButton {
    background: #eef2f9; color: #1e2230;
    border: 1px solid #c7d0e0; border-radius: 6px; padding: 6px 12px;
}
QPushButton:hover, QToolButton:hover { background: #e1e8f5; }

QLabel { background: transparent; }
QMenu { background: #ffffff; border: 1px solid #c7d0e0; padding: 6px; }
QMenu::item { padding: 8px 28px 8px 12px; border-radius: 6px; }
QMenu::item:selected { background: #3b6ea5; color: white; }
QComboBox { background: #eef2f9; border: 1px solid #c7d0e0; border-radius: 6px; padding: 4px 8px; }

#Taskbar { background: #dde3ee; border-top: 1px solid #c7d0e0; }
#StartButton { background: #3b6ea5; color: white; font-weight: bold; border: none; border-radius: 6px; }
#StartButton:hover { background: #4a82c0; }
#Clock { color: #1e2230; padding-right: 8px; }
#NetButton { background: transparent; border: none; color: #1e2230; padding: 4px 10px; }
#NetButton:hover { background: #cdd5e3; border-radius: 6px; }
#DesktopIcons { background: transparent; }
QMdiSubWindow { background: #ffffff; }
QMdiSubWindow > QWidget { background: #ffffff; }
"""


def theme_qss(name: str) -> str:
    return QSS_LIGHT if name == "light" else QSS_DARK
