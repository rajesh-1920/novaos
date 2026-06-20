#!/usr/bin/env sh
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
#
# Launch NovaOS Desktop.
cd "$(dirname "$0")" || exit 1
exec python3 -m novaos_desktop "$@"
