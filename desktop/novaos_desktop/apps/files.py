# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Files - a simple file manager for the sandboxed NovaFS drive."""
from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QInputDialog, QMessageBox, Qt, QSize,
)

from ..icons import make_icon


class Files(QWidget):
    def __init__(self, fs, open_file=None):
        super().__init__()
        self.fs = fs
        self.open_file = open_file or (lambda path: None)
        self.cwd = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        self.up_btn = QPushButton("Up")
        self.up_btn.clicked.connect(self._go_up)
        self.new_btn = QPushButton("New Folder")
        self.new_btn.clicked.connect(self._new_folder)
        self.del_btn = QPushButton("Delete")
        self.del_btn.clicked.connect(self._delete)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)
        for b in (self.up_btn, self.new_btn, self.del_btn, self.refresh_btn):
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.path_label = QLabel()
        layout.addWidget(self.path_label)

        self.listw = QListWidget()
        self.listw.setIconSize(QSize(28, 28))
        self.listw.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self.listw, 1)

        self.refresh()

    def refresh(self):
        self.path_label.setText("Drive: /" + self.cwd)
        self.listw.clear()
        for name in self.fs.listdir(self.cwd):
            child = self.fs.join(self.cwd, name)
            is_dir = self.fs.is_dir(child)
            icon = make_icon("D" if is_dir else "·",
                             "#3b6ea5" if is_dir else "#64748b")
            item = QListWidgetItem(icon, name + ("/" if is_dir else ""))
            item.setData(Qt.UserRole, (name, is_dir))
            self.listw.addItem(item)

    def _go_up(self):
        if self.cwd:
            self.cwd = self.fs.join(self.cwd, "..")
            self.refresh()

    def _open_item(self, item):
        name, is_dir = item.data(Qt.UserRole)
        target = self.fs.join(self.cwd, name)
        if is_dir:
            self.cwd = target
            self.refresh()
        else:
            self.open_file(target)

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            self.fs.mkdir(self.fs.join(self.cwd, name.strip()))
            self.refresh()

    def _delete(self):
        item = self.listw.currentItem()
        if item is None:
            return
        name, _ = item.data(Qt.UserRole)
        if QMessageBox.question(self, "Delete", f"Delete '{name}'?") == QMessageBox.Yes:
            try:
                self.fs.remove(self.fs.join(self.cwd, name))
            except OSError as exc:
                QMessageBox.warning(self, "Delete failed", str(exc))
            self.refresh()
