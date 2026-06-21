# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Camera - a webcam app for NovaOS Desktop.

Shows a live preview and saves snapshots into the NovaOS sandboxed drive
(Pictures/). Frames are grabbed on a background thread with OpenCV and handed
to the GUI via a signal, so the desktop never freezes. If OpenCV isn't
installed it shows how to enable it instead of failing.
"""
import threading
import time

from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QImage, QPixmap, Qt, Signal,
)

try:
    import cv2
    HAVE_CV2 = True
except Exception:
    HAVE_CV2 = False


class Camera(QWidget):
    _frame = Signal(object)        # QImage
    _status = Signal(str)

    def __init__(self, fs):
        super().__init__()
        self.fs = fs
        self._thread = None
        self._stop = threading.Event()
        self._last = None          # most recent QImage (for capture)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.view = QLabel()
        self.view.setAlignment(Qt.AlignCenter)
        self.view.setMinimumSize(480, 360)
        self.view.setStyleSheet("background:#0c0e16; border-radius:6px; color:#8a93a8;")
        self.view.setText("Camera off")
        layout.addWidget(self.view, 1)

        controls = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop)
        self.capture_btn = QPushButton("Capture")
        self.capture_btn.clicked.connect(self.capture)
        for b in (self.start_btn, self.stop_btn, self.capture_btn):
            controls.addWidget(b)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.status = QLabel()
        self.status.setStyleSheet("color:#8a93a8; font-size:11px;")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self._frame.connect(self._on_frame)
        self._status.connect(self.status.setText)

        if not HAVE_CV2:
            for b in (self.start_btn, self.stop_btn, self.capture_btn):
                b.setEnabled(False)
            self.view.setText("No camera backend")
            self.status.setText(
                "OpenCV is not installed. Enable the camera with one of:\n"
                "  sudo apt install python3-opencv      (system-wide)\n"
                "  pip install opencv-python-headless   (in a venv)")
        else:
            self.stop_btn.setEnabled(False)
            self.status.setText("Ready. Press Start.")

    # -- capture loop -------------------------------------------------------
    def start(self):
        if not HAVE_CV2 or (self._thread and self._thread.is_alive()):
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._emit_status("Starting camera…")

    def _loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            cap.release()
            self._emit_status("Could not open the camera (/dev/video0).")
            self._reset_buttons()
            return
        self._emit_status("Camera live.")
        while not self._stop.is_set():
            ok, frame = cap.read()
            if not ok:
                self._emit_status("Camera read failed.")
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = rgb.shape
            img = QImage(rgb.tobytes(), w, h, 3 * w, QImage.Format_RGB888).copy()
            self._emit_frame(img)
            self._stop.wait(0.03)          # ~30 fps cap
        cap.release()

    def stop(self):
        self._stop.set()
        self._thread = None
        self._last = None
        self.view.setText("Camera off")
        self.view.setPixmap(QPixmap())
        self._reset_buttons()
        self.status.setText("Stopped.")

    def capture(self):
        if self._last is None:
            self.status.setText("Nothing to capture yet — start the camera first.")
            return
        rel = "Pictures/capture-" + time.strftime("%Y%m%d-%H%M%S") + ".png"
        try:
            self._last.save(self.fs.real_path(rel))
            self.status.setText("Saved /" + rel)
        except Exception as exc:           # noqa: BLE001
            self.status.setText(f"Could not save: {exc}")

    # -- helpers (signals are safe if the window was closed) ----------------
    def _on_frame(self, img):
        self._last = img
        self.view.setPixmap(QPixmap.fromImage(img).scaled(
            self.view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _reset_buttons(self):
        self.start_btn.setEnabled(HAVE_CV2)
        self.stop_btn.setEnabled(False)

    def _emit_frame(self, img):
        try:
            self._frame.emit(img)
        except RuntimeError:
            self._stop.set()

    def _emit_status(self, text):
        try:
            self._status.emit(text)
        except RuntimeError:
            self._stop.set()

    def closeEvent(self, event):
        self._stop.set()
        super().closeEvent(event)
