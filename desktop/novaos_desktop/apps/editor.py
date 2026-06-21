# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Editor - a plain-text editor that reads/writes files on the NovaFS drive."""
from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton,
    QLabel, QInputDialog, QMessageBox, QFont,
)


class Editor(QWidget):
    def __init__(self, fs):
        super().__init__()
        self.fs = fs
        self.path = None                    # current file path on the drive

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._new)
        new_btn.setShortcut("Ctrl+N")
        open_btn = QPushButton("Open")
        open_btn.clicked.connect(self._open)
        open_btn.setShortcut("Ctrl+O")
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        save_btn.setShortcut("Ctrl+S")
        for b in (new_btn, open_btn, save_btn):
            b.setToolTip(b.text() + "  (" + b.shortcut().toString() + ")")
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        self.status = QLabel("untitled")
        toolbar.addWidget(self.status)
        layout.addLayout(toolbar)

        self.text = QPlainTextEdit()
        self.text.setFont(QFont("Monospace", 11))
        layout.addWidget(self.text, 1)

    # -- public -------------------------------------------------------------
    def open_path(self, path):
        if not self.fs.is_file(path):
            return
        with open(self.fs.real_path(path), "rb") as fh:
            raw = fh.read()
        if b"\x00" in raw[:8192]:            # looks binary
            self.text.setPlainText(
                f"[binary file - {len(raw)} bytes]\n\n"
                "This file is not text. Images open in the Image Viewer "
                "(double-click them in Files).")
            self.path = None
            self.status.setText("/" + path + "  (binary, read-only)")
            return
        self.text.setPlainText(raw.decode("utf-8", errors="replace"))
        self.path = path
        self.status.setText("/" + path)

    # -- actions ------------------------------------------------------------
    def _new(self):
        self.text.clear()
        self.path = None
        self.status.setText("untitled")

    def _open(self):
        files = [n for n in self.fs.listdir("") if self.fs.is_file(n)]
        # include files in Documents for convenience
        for n in self.fs.listdir("Documents"):
            if self.fs.is_file("Documents/" + n):
                files.append("Documents/" + n)
        if not files:
            QMessageBox.information(self, "Open", "No files on the drive yet.")
            return
        name, ok = QInputDialog.getItem(self, "Open file", "File:", files, 0, False)
        if ok and name:
            self.open_path(name)

    def _save(self):
        if self.path is None:
            name, ok = QInputDialog.getText(self, "Save As", "File name:", text="untitled.txt")
            if not (ok and name.strip()):
                return
            self.path = "Documents/" + name.strip()
        self.fs.write(self.path, self.text.toPlainText())
        self.status.setText("/" + self.path + "  (saved)")
