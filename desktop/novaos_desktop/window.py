# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""AppWindow - a QMdiSubWindow that announces when it closes.

The desktop needs to drop a window's taskbar button when it closes; the base
QMdiSubWindow has no such signal, so we add one.
"""
from .qt import QMdiSubWindow, Signal


class AppWindow(QMdiSubWindow):
    closed = Signal(object)

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)
