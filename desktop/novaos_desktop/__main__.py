# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Entry point: `python -m novaos_desktop`.

Flags:
  --selftest            open a few apps then quit (used for CI/smoke tests)
  --screenshot PATH     render the desktop to PATH (PNG) then quit
"""
import sys

from .qt import QApplication, QTimer, run_app
from .filesystem import NovaFS
from .app import NovaDesktop


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)

    selftest = "--selftest" in argv
    shot = None
    if "--screenshot" in argv:
        i = argv.index("--screenshot")
        shot = argv[i + 1] if i + 1 < len(argv) else "novaos_desktop.png"

    app = QApplication(argv)
    desktop = NovaDesktop(NovaFS())
    desktop.show()

    if selftest or shot:
        desktop.resize(1280, 800)
        for name in ("Terminal", "Files", "Calculator"):
            desktop.launch_app(name)
        for _ in range(3):
            QApplication.processEvents()
        if shot:
            desktop.grab().save(shot)
            print(f"saved screenshot to {shot}")
        QTimer.singleShot(200, app.quit)

    return run_app(app)


if __name__ == "__main__":
    sys.exit(main())
