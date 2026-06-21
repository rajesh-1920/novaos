# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Terminal - a small interactive shell for NovaOS Desktop.

Output goes to a read-only text area; commands are typed in a one-line input.
Filesystem commands operate on the sandboxed NovaFS. A few commands (open/apps)
talk back to the desktop via callbacks.
"""
from ..qt import QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit, QLabel, QFont, Qt

from .. import __version__

BANNER = r"""
    _   __                 ____  _____
   / | / /___ _   ______ _/ __ \/ ___/
  /  |/ / __ \ | / / __ `/ / / /\__ \
 / /|  / /_/ / |/ / /_/ / /_/ /___/ /
/_/ |_/\____/|___/\__,_/\____//____/   Desktop
"""


class _CmdEdit(QLineEdit):
    """Command input with Up/Down history recall."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Up:
            self.owner._history_prev()
        elif event.key() == Qt.Key_Down:
            self.owner._history_next()
        else:
            super().keyPressEvent(event)


class Terminal(QWidget):
    def __init__(self, fs, launch_app=None, system_info=None, get_username=None):
        super().__init__()
        self.fs = fs
        self.launch_app = launch_app or (lambda *a, **k: None)
        self.system_info = system_info or (lambda: {})
        self.get_username = get_username or (lambda: "nova")
        self.cwd = ""                       # current dir, relative to drive root
        self._history = []                  # command history
        self._hist = 0                      # cursor into history

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.output = QPlainTextEdit(readOnly=True)
        self.output.setFont(QFont("Monospace", 11))
        layout.addWidget(self.output)

        row = QHBoxLayout()
        self.prompt = QLabel(self._prompt_text())
        self.prompt.setFont(QFont("Monospace", 11))
        self.input = _CmdEdit(self)
        self.input.setFont(QFont("Monospace", 11))
        self.input.returnPressed.connect(self._on_enter)
        row.addWidget(self.prompt)
        row.addWidget(self.input, 1)
        layout.addLayout(row)

        self._println(BANNER)
        self._println(f"NovaOS Desktop shell {__version__}. Type 'help' for commands.\n")
        self.input.setFocus()

    # -- helpers ------------------------------------------------------------
    def _prompt_text(self):
        path = "/" + self.cwd if self.cwd else "/"
        return f"{self.get_username()}@nova:{path}$"

    def _println(self, text=""):
        self.output.appendPlainText(text)

    def _refresh_prompt(self):
        self.prompt.setText(self._prompt_text())

    def _on_enter(self):
        line = self.input.text()
        self.input.clear()
        if line.strip():
            self._history.append(line)
        self._hist = len(self._history)
        self._println(f"{self._prompt_text()} {line}")
        self._run(line.strip())
        self._refresh_prompt()
        bar = self.output.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _history_prev(self):
        if not self._history:
            return
        if self._hist > 0:
            self._hist -= 1
        self.input.setText(self._history[self._hist])
        self.input.end(False)

    def _history_next(self):
        if not self._history:
            return
        if self._hist < len(self._history) - 1:
            self._hist += 1
            self.input.setText(self._history[self._hist])
            self.input.end(False)
        else:
            self._hist = len(self._history)
            self.input.clear()

    # -- command dispatch ---------------------------------------------------
    def _run(self, line):
        if not line:
            return
        parts = line.split()
        cmd, args = parts[0], parts[1:]
        handler = getattr(self, f"_cmd_{cmd}", None)
        if handler is None:
            self._println(f"nova-sh: command not found: {cmd}  (try 'help')")
        else:
            try:
                handler(args)
            except Exception as exc:                      # never let the shell die
                self._println(f"error: {exc}")

    # -- commands -----------------------------------------------------------
    def _cmd_help(self, args):
        self._println(
            "commands:\n"
            "  help              show this help\n"
            "  about             about NovaOS Desktop\n"
            "  neofetch          system info + logo\n"
            "  ls [dir]          list directory\n"
            "  cd [dir]          change directory\n"
            "  pwd               print working directory\n"
            "  cat <file>        print a file\n"
            "  mkdir <dir>       make a directory\n"
            "  touch <file>      create an empty file\n"
            "  rm <name>         remove a file/empty dir\n"
            "  echo <text>       print text\n"
            "  date              current date/time\n"
            "  whoami            current user\n"
            "  calc <expr>       evaluate a math expression\n"
            "  apps              list available apps\n"
            "  open <app>        launch an app (e.g. open Files)\n"
            "  clear             clear the screen"
        )

    def _cmd_clear(self, args):
        self.output.clear()

    def _cmd_echo(self, args):
        self._println(" ".join(args))

    def _cmd_about(self, args):
        info = self.system_info()
        self._println(f"{info.get('os', 'NovaOS Desktop')} {info.get('version', '')}")
        self._println("A simulated OS desktop, companion to the NovaOS kernel.")

    def _cmd_whoami(self, args):
        self._println(self.get_username())

    def _cmd_date(self, args):
        from datetime import datetime
        self._println(datetime.now().strftime("%a %d %b %Y  %H:%M:%S"))

    def _cmd_pwd(self, args):
        self._println("/" + self.cwd if self.cwd else "/")

    def _cmd_ls(self, args):
        target = self.fs.join(self.cwd, args[0]) if args else self.cwd
        if not self.fs.is_dir(target):
            self._println(f"ls: not a directory: {args[0] if args else '/'}")
            return
        entries = self.fs.listdir(target)
        if not entries:
            return
        out = []
        for name in entries:
            child = self.fs.join(target, name)
            out.append(name + "/" if self.fs.is_dir(child) else name)
        self._println("  ".join(out))

    def _cmd_cd(self, args):
        if not args or args[0] == "/":
            self.cwd = ""
            return
        new = self.fs.join(self.cwd, args[0])
        if self.fs.is_dir(new):
            self.cwd = new
        else:
            self._println(f"cd: no such directory: {args[0]}")

    def _cmd_cat(self, args):
        if not args:
            self._println("usage: cat <file>")
            return
        path = self.fs.join(self.cwd, args[0])
        if not self.fs.is_file(path):
            self._println(f"cat: no such file: {args[0]}")
            return
        self._println(self.fs.read(path).rstrip("\n"))

    def _cmd_mkdir(self, args):
        if not args:
            self._println("usage: mkdir <dir>")
            return
        self.fs.mkdir(self.fs.join(self.cwd, args[0]))

    def _cmd_touch(self, args):
        if not args:
            self._println("usage: touch <file>")
            return
        self.fs.touch(self.fs.join(self.cwd, args[0]))

    def _cmd_rm(self, args):
        if not args:
            self._println("usage: rm <name>")
            return
        path = self.fs.join(self.cwd, args[0])
        if not self.fs.exists(path):
            self._println(f"rm: no such file or directory: {args[0]}")
            return
        self.fs.remove(path)

    def _cmd_calc(self, args):
        expr = "".join(args)
        allowed = set("0123456789+-*/().% ")
        if not expr or set(expr) - allowed:
            self._println("calc: only numbers and + - * / ( ) % are allowed")
            return
        self._println(str(eval(expr, {"__builtins__": {}}, {})))

    def _cmd_apps(self, args):
        info = self.system_info()
        self._println("  ".join(info.get("apps", [])))

    def _cmd_open(self, args):
        if not args:
            self._println("usage: open <app>   (see 'apps')")
            return
        self.launch_app(args[0])
        self._println(f"launching {args[0]}...")

    def _cmd_neofetch(self, args):
        info = self.system_info()
        lines = [
            f"{self.get_username()}@nova",
            "-----------",
            f"OS:      {info.get('os', 'NovaOS Desktop')} {info.get('version', '')}",
            f"Kernel:  companion to NovaOS (x86_64)",
            f"Shell:   nova-sh",
            f"Theme:   {info.get('theme', 'dark')}",
            f"Wallpaper: {info.get('wallpaper', '-')}",
            f"Apps:    {len(info.get('apps', []))} installed",
        ]
        logo = BANNER.strip("\n").splitlines()
        width = max((len(l) for l in logo), default=0)
        for i in range(max(len(logo), len(lines))):
            left = logo[i] if i < len(logo) else ""
            right = lines[i] if i < len(lines) else ""
            self._println(f"{left.ljust(width)}   {right}")
