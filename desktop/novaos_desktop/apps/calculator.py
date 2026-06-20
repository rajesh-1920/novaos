# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Calculator - a basic four-function calculator."""
from ..qt import QWidget, QVBoxLayout, QGridLayout, QPushButton, QLineEdit, Qt, QFont


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.display = QLineEdit("0")
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignRight)
        self.display.setFont(QFont("Monospace", 20))
        self.display.setMinimumHeight(48)
        layout.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(6)
        buttons = [
            ("C", 0, 0), ("(", 0, 1), (")", 0, 2), ("/", 0, 3),
            ("7", 1, 0), ("8", 1, 1), ("9", 1, 2), ("*", 1, 3),
            ("4", 2, 0), ("5", 2, 1), ("6", 2, 2), ("-", 2, 3),
            ("1", 3, 0), ("2", 3, 1), ("3", 3, 2), ("+", 3, 3),
            ("0", 4, 0), (".", 4, 1), ("=", 4, 2), ("%", 4, 3),
        ]
        for label, r, c in buttons:
            btn = QPushButton(label)
            btn.setMinimumSize(56, 48)
            btn.setFont(QFont("Sans Serif", 14))
            btn.clicked.connect(lambda _=False, t=label: self._press(t))
            grid.addWidget(btn, r, c)
        layout.addLayout(grid)
        self._reset = True

    def _press(self, token):
        if token == "C":
            self.display.setText("0")
            self._reset = True
            return
        if token == "=":
            self._evaluate()
            return
        current = self.display.text()
        if self._reset or current == "0":
            current = ""
            self._reset = False
        if token.isdigit() or token in ".+-*/()%":
            self.display.setText(current + token)

    def _evaluate(self):
        expr = self.display.text()
        allowed = set("0123456789+-*/().% ")
        if set(expr) - allowed:
            self.display.setText("error")
            self._reset = True
            return
        try:
            result = eval(expr, {"__builtins__": {}}, {})
            self.display.setText(str(result))
        except Exception:
            self.display.setText("error")
        self._reset = True
