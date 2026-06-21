# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Files - a file manager for the sandboxed NovaFS drive.

Clipboard keys act on *files* and are scoped to the file list, so they don't
clash with text fields (which keep their own Ctrl+C/V/X/Z/A):
  Ctrl+C copy, Ctrl+X cut, Ctrl+V paste, Ctrl+A select-all, Ctrl+Z undo,
  Delete (-> Trash), Enter (open), Backspace (up), F5 (refresh).
Deletes move items to a hidden .novaos-trash folder so they can be undone.
"""
import os
import shutil

from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QInputDialog, QMessageBox, QAbstractItemView, Qt, QSize,
)

from ..icons import make_icon

TRASH = ".novaos-trash"


class _FileList(QListWidget):
    """List that routes file-manager keys to the Files app (only when focused,
    so it never steals Ctrl+C/V/X/Z/Delete from text fields elsewhere)."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def keyPressEvent(self, event):
        key = event.key()
        ctrl = bool(event.modifiers() & Qt.ControlModifier)
        if ctrl and key == Qt.Key_C:
            self.owner._copy()
        elif ctrl and key == Qt.Key_X:
            self.owner._cut()
        elif ctrl and key == Qt.Key_V:
            self.owner._paste()
        elif ctrl and key == Qt.Key_A:
            self.owner._select_all()
        elif ctrl and key == Qt.Key_Z:
            self.owner._undo_last()
        elif key == Qt.Key_Delete:
            self.owner._delete()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self.owner._open_selected()
        elif key == Qt.Key_Backspace:
            self.owner._go_up()
        elif key == Qt.Key_F5:
            self.owner.refresh()
        else:
            super().keyPressEvent(event)


class Files(QWidget):
    def __init__(self, fs, open_file=None):
        super().__init__()
        self.fs = fs
        self.open_file = open_file or (lambda path: None)
        self.cwd = ""
        self._clip = None          # (mode, [rel paths]); mode = "copy" | "cut"
        self._undo = None          # callable that reverses the last operation

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        toolbar = QHBoxLayout()
        specs = [
            ("Up", self._go_up, "Go up (Backspace)"),
            ("New Folder", self._new_folder, "New folder"),
            ("Copy", self._copy, "Copy (Ctrl+C)"),
            ("Cut", self._cut, "Cut (Ctrl+X)"),
            ("Paste", self._paste, "Paste (Ctrl+V)"),
            ("Delete", self._delete, "Move to Trash (Delete)"),
            ("Refresh", self.refresh, "Refresh (F5)"),
        ]
        for label, slot, tip in specs:
            b = QPushButton(label)
            b.clicked.connect(slot)
            b.setToolTip(tip)
            toolbar.addWidget(b)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.path_label = QLabel()
        layout.addWidget(self.path_label)

        self.listw = _FileList(self)
        self.listw.setIconSize(QSize(28, 28))
        self.listw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.listw.itemDoubleClicked.connect(self._open_item)
        layout.addWidget(self.listw, 1)

        hint = QLabel("Keys: Ctrl+C/X/V copy·cut·paste · Ctrl+A all · "
                      "Ctrl+Z undo · Delete · Enter open · Backspace up")
        hint.setStyleSheet("color:#8a93a8; font-size:11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.refresh()

    # -- listing ------------------------------------------------------------
    def refresh(self):
        self.path_label.setText("Drive: /" + self.cwd)
        self.listw.clear()
        for name in self.fs.listdir(self.cwd):
            if name.startswith("."):          # hide dotfiles (incl. Trash)
                continue
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

    def _open_selected(self):
        item = self.listw.currentItem()
        if item is not None:
            self._open_item(item)

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
        if ok and name.strip():
            self.fs.mkdir(self.fs.join(self.cwd, name.strip()))
            self.refresh()

    # -- selection / clipboard ---------------------------------------------
    def _selected(self):
        return [it.data(Qt.UserRole) for it in self.listw.selectedItems()]

    def _select_all(self):
        self.listw.selectAll()

    def _copy(self):
        items = self._selected()
        if items:
            self._clip = ("copy", [self.fs.join(self.cwd, n) for n, _ in items])

    def _cut(self):
        items = self._selected()
        if items:
            self._clip = ("cut", [self.fs.join(self.cwd, n) for n, _ in items])

    def _unique_dest(self, dir_rel, name):
        candidate = self.fs.join(dir_rel, name)
        if not self.fs.exists(candidate):
            return candidate
        if "." in name and not name.startswith("."):
            stem, _, ext = name.rpartition(".")
            ext = "." + ext
        else:
            stem, ext = name, ""
        i = 1
        while True:
            suffix = " (copy)" if i == 1 else f" (copy {i})"
            candidate = self.fs.join(dir_rel, f"{stem}{suffix}{ext}")
            if not self.fs.exists(candidate):
                return candidate
            i += 1

    def _paste(self):
        if not self._clip:
            return
        mode, sources = self._clip
        created, moved = [], []
        for src_rel in sources:
            if not self.fs.exists(src_rel):
                continue
            name = src_rel.rsplit("/", 1)[-1]
            dest_rel = self._unique_dest(self.cwd, name)
            src, dst = self.fs.real_path(src_rel), self.fs.real_path(dest_rel)
            try:
                if mode == "copy":
                    if self.fs.is_dir(src_rel):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                    created.append(dest_rel)
                else:
                    shutil.move(src, dst)
                    moved.append((src_rel, dest_rel))
            except (OSError, shutil.Error) as exc:
                QMessageBox.warning(self, "Paste failed", str(exc))

        if mode == "cut":
            self._clip = None
            if moved:
                self._undo = lambda: self._reverse_moves([(d, s) for s, d in moved])
        elif created:
            self._undo = lambda: self._remove_paths(created)
        self.refresh()

    # -- delete (to Trash) + undo ------------------------------------------
    def _delete(self):
        items = self._selected()
        if not items:
            return
        if QMessageBox.question(
                self, "Delete",
                f"Move {len(items)} item(s) to Trash?") != QMessageBox.Yes:
            return
        self.fs.mkdir(TRASH)
        moved = []
        for name, _ in items:
            src_rel = self.fs.join(self.cwd, name)
            if not self.fs.exists(src_rel):
                continue
            dest_rel = self._unique_dest(TRASH, name)
            try:
                shutil.move(self.fs.real_path(src_rel), self.fs.real_path(dest_rel))
                moved.append((src_rel, dest_rel))
            except OSError as exc:
                QMessageBox.warning(self, "Delete failed", str(exc))
        if moved:
            self._undo = lambda: self._reverse_moves([(d, s) for s, d in moved])
        self.refresh()

    # -- undo helpers -------------------------------------------------------
    def _undo_last(self):
        if self._undo is not None:
            fn, self._undo = self._undo, None
            fn()

    def _reverse_moves(self, pairs):
        for src_rel, dest_rel in pairs:
            try:
                shutil.move(self.fs.real_path(src_rel), self.fs.real_path(dest_rel))
            except OSError:
                pass
        self.refresh()

    def _remove_paths(self, rels):
        for rel in rels:
            p = self.fs.real_path(rel)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
            elif os.path.exists(p):
                os.remove(p)
        self.refresh()
