# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""NovaFS - a small sandboxed virtual filesystem.

Everything the desktop's apps read or write lives under a single "drive"
directory (default: ~/.novaos_desktop/drive). All paths are treated as POSIX
paths relative to that root, and any attempt to escape it (via .. or absolute
paths) is clamped back to the root. This keeps the simulated OS self-contained
and unable to touch the user's real files by accident.
"""
import os


class NovaFS:
    def __init__(self, root: str | None = None):
        if root is None:
            root = os.path.join(os.path.expanduser("~"), ".novaos_desktop", "drive")
        self.root = os.path.abspath(root)
        self._ensure_defaults()

    # -- internal -----------------------------------------------------------
    def _resolve(self, rel: str):
        """Map a relative path to (absolute, normalized-rel), clamped to root."""
        parts: list[str] = []
        for seg in str(rel).replace("\\", "/").split("/"):
            if seg in ("", "."):
                continue
            if seg == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(seg)
        full = os.path.abspath(os.path.join(self.root, *parts))
        if full != self.root and not full.startswith(self.root + os.sep):
            return self.root, ""
        return full, "/".join(parts)

    def _ensure_defaults(self):
        os.makedirs(self.root, exist_ok=True)
        for folder in ("Documents", "Pictures", "Music"):
            os.makedirs(os.path.join(self.root, folder), exist_ok=True)
        welcome = os.path.join(self.root, "Documents", "welcome.txt")
        if not os.path.exists(welcome):
            with open(welcome, "w", encoding="utf-8") as fh:
                fh.write(
                    "Welcome to NovaOS Desktop!\n\n"
                    "This is your virtual drive. It is completely sandboxed:\n"
                    "apps here can only see files under this drive.\n\n"
                    "Try the Terminal:  type 'help', or 'neofetch'.\n"
                )

    # -- public API ---------------------------------------------------------
    def normalize(self, rel: str) -> str:
        return self._resolve(rel)[1]

    def exists(self, rel: str) -> bool:
        return os.path.exists(self._resolve(rel)[0])

    def is_dir(self, rel: str) -> bool:
        return os.path.isdir(self._resolve(rel)[0])

    def is_file(self, rel: str) -> bool:
        return os.path.isfile(self._resolve(rel)[0])

    def listdir(self, rel: str = ""):
        full = self._resolve(rel)[0]
        if not os.path.isdir(full):
            return []
        entries = os.listdir(full)
        # directories first, then files, both alphabetical
        return sorted(entries, key=lambda n: (not os.path.isdir(os.path.join(full, n)), n.lower()))

    def read(self, rel: str) -> str:
        with open(self._resolve(rel)[0], "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()

    def write(self, rel: str, text: str):
        full, norm = self._resolve(rel)
        if not norm:
            raise ValueError("invalid path")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(text)

    def mkdir(self, rel: str):
        full, norm = self._resolve(rel)
        if not norm:
            raise ValueError("invalid path")
        os.makedirs(full, exist_ok=True)

    def touch(self, rel: str):
        if not self.exists(rel):
            self.write(rel, "")

    def remove(self, rel: str):
        full, norm = self._resolve(rel)
        if not norm:
            raise ValueError("cannot remove the drive root")
        if os.path.isdir(full):
            os.rmdir(full)            # only removes empty dirs (safe)
        elif os.path.exists(full):
            os.remove(full)

    def real_path(self, rel: str) -> str:
        return self._resolve(rel)[0]

    def join(self, base: str, name: str) -> str:
        return self._resolve(base + "/" + name)[1]
