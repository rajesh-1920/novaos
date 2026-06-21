# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""ImageViewer - displays image files from the NovaOS sandboxed drive.

Renders PNG/JPEG/GIF/BMP/etc. with Qt's built-in image loaders (no extra
dependencies), scaling to fit the window. This is what image files open in,
instead of the text Editor (which would show their raw bytes).
"""
from ..qt import QWidget, QVBoxLayout, QLabel, QPixmap, Qt

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
              ".ico", ".tif", ".tiff", ".pbm", ".pgm", ".ppm", ".xbm", ".xpm")


def is_image(path: str) -> bool:
    return path.lower().endswith(IMAGE_EXTS)


class ImageViewer(QWidget):
    def __init__(self, fs):
        super().__init__()
        self.fs = fs
        self._pix = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.label = QLabel("No image")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("background:#0c0e16; border-radius:6px; color:#8a93a8;")
        layout.addWidget(self.label, 1)

        self.status = QLabel()
        self.status.setStyleSheet("color:#8a93a8; font-size:11px;")
        layout.addWidget(self.status)

    def open_path(self, rel):
        pix = QPixmap(self.fs.real_path(rel))
        if pix.isNull():
            self._pix = None
            self.label.setText("Cannot display this image.")
            self.status.setText("/" + rel)
            return
        self._pix = pix
        self.status.setText(f"/{rel}    ({pix.width()} × {pix.height()})")
        self._rescale()

    def _rescale(self):
        if self._pix is not None:
            self.label.setPixmap(self._pix.scaled(
                self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        self._rescale()
        super().resizeEvent(event)
