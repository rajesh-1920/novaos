#!/usr/bin/env sh
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
#
# Launch NovaOS Desktop.
cd "$(dirname "$0")" || exit 1

# Prefer the local venv (it has OpenCV for the Camera app); otherwise fall
# back to the system Python.
VENV="$HOME/.novaos_desktop/venv"
if [ -x "$VENV/bin/python" ]; then
    PYTHON="$VENV/bin/python"
else
    PYTHON="python3"
fi
exec "$PYTHON" -m novaos_desktop "$@"
