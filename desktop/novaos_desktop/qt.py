# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Qt binding shim.

Prefer PySide6, but transparently fall back to PyQt5 (whichever is actually
importable on this machine). Every module imports its Qt classes from here, so
the rest of the app never names a specific binding.
"""

try:
    from PySide6.QtCore import (
        Qt, QTimer, QSize, QPoint, QRectF, QUrl, Signal,
    )
    from PySide6.QtGui import (
        QIcon, QPixmap, QPainter, QColor, QFont, QBrush, QLinearGradient, QGradient,
        QImage,
    )
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QFormLayout, QMdiArea, QMdiSubWindow, QFrame, QPushButton, QToolButton,
        QLabel, QMenu, QPlainTextEdit, QLineEdit, QListWidget, QListWidgetItem,
        QComboBox, QInputDialog, QMessageBox, QTextBrowser,
        QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    )
    BINDING = "PySide6"
except ImportError:  # fall back to PyQt5
    from PyQt5.QtCore import (
        Qt, QTimer, QSize, QPoint, QRectF, QUrl, pyqtSignal as Signal,
    )
    from PyQt5.QtGui import (
        QIcon, QPixmap, QPainter, QColor, QFont, QBrush, QLinearGradient, QGradient,
        QImage,
    )
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QFormLayout, QMdiArea, QMdiSubWindow, QFrame, QPushButton, QToolButton,
        QLabel, QMenu, QPlainTextEdit, QLineEdit, QListWidget, QListWidgetItem,
        QComboBox, QInputDialog, QMessageBox, QTextBrowser,
        QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    )
    BINDING = "PyQt5"


def run_app(app):
    """QApplication event loop, compatible with both bindings."""
    return app.exec() if hasattr(app, "exec") else app.exec_()
