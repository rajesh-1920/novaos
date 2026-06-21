# NovaOS Desktop

A **simulated operating-system desktop** that runs as a normal desktop
application — wallpaper, taskbar, Start menu, draggable/resizable app windows,
and a set of built-in apps. It is the GUI companion to the
[NovaOS kernel](../README.md): the kernel *is* a tiny OS; this app *looks and
behaves like* an OS desktop, written in Python.

It is **not** a virtual machine — it's a desktop environment simulation
(think "an OS-style desktop inside one window").

```
 Desktop icons        Draggable app windows                Taskbar
 ┌──────────┐   ┌───────────────┐ ┌──────────────┐
 │ Terminal │   │  Terminal     │ │  Calculator  │
 │ Files    │   │  $ neofetch   │ │  [7][8][9]   │
 │ Editor   │   └───────────────┘ └──────────────┘
 │ About    │
 └──────────┘   [ Start ]  [Terminal][Files][Calc]      Sun 21 Jun 00:30
```

## Run it

```sh
cd desktop
./run.sh
# or:  python3 -m novaos_desktop
```

### Requirements
A Qt binding for Python — **either PySide6 or PyQt5**. The app auto-detects
whichever is installed (see `novaos_desktop/qt.py`). On this machine PyQt5 is
already present, so no install is needed. Otherwise:

```sh
pip install -r requirements.txt        # PySide6
# or:  sudo apt install python3-pyqt5
```

## Built-in apps

| App         | What it does                                                  |
|-------------|--------------------------------------------------------------|
| **Terminal**| A shell: `help`, `ls`, `cd`, `cat`, `mkdir`, `touch`, `rm`, `echo`, `calc`, `date`, `neofetch`, `open <app>`, `clear` |
| **Files**   | Browse/create/delete files & folders on the virtual drive    |
| **Browser** | Web browser — Chromium (Qt WebEngine) if installed, else a built-in lite engine (urllib + QTextBrowser) with address bar, back/forward and search |
| **Network** | **Sandboxed** Wi-Fi manager: a *virtual* NovaOS network you can turn on/off, connect and disconnect. It gates NovaOS apps (the Browser goes offline when it's off) but **never changes your computer's real Wi-Fi**. Shows a read-only scan of nearby networks for realism. |
| **Monitor** | Task manager for NovaOS Desktop: lists the **NovaOS apps** currently running (PID, app, status, uptime) &mdash; *not* the host computer's processes. Shows NovaOS Desktop's own CPU/RAM footprint; **End Task** closes the selected app and **Switch To** focuses it. |
| **Editor**  | Open, edit and save text files                               |
| **Calculator** | Four-function calculator                                  |
| **Settings**| Change wallpaper, theme (dark/light) and username           |
| **About**   | Info about NovaOS Desktop                                    |

Open apps from the **desktop icons**, the **Start menu**, or the Terminal
(`open Files`). Windows can be moved, resized, minimized, maximized and closed;
the taskbar tracks open windows and shows a live clock.

## Where files live

All app file I/O is sandboxed to a **virtual drive** at
`~/.novaos_desktop/drive/`. Apps cannot read or write outside it, so the
simulated OS can't touch your real files by accident.

## Project layout

```
desktop/
├── run.sh                     # launcher
├── requirements.txt
└── novaos_desktop/
    ├── __main__.py            # entry point (python -m novaos_desktop)
    ├── qt.py                  # Qt binding shim (PySide6 -> PyQt5 fallback)
    ├── app.py                 # NovaDesktop: wallpaper, taskbar, window mgmt
    ├── window.py              # AppWindow (MDI subwindow w/ close signal)
    ├── icons.py               # painted app icons (no image assets)
    ├── style.py               # themes + wallpaper brushes
    ├── filesystem.py          # NovaFS sandboxed virtual drive
    └── apps/                  # terminal, files, browser, network, monitor, editor, calculator, settings, about
```

## Developer notes

- **Add an app:** drop a `QWidget` subclass in `novaos_desktop/apps/`, then add
  an entry to `APP_SPECS` (icon letter + color) and a branch in
  `NovaDesktop._create_widget()` in `app.py`. It then appears on the desktop,
  in the Start menu, and via `open <name>` in the Terminal.
- **Headless self-test / screenshot:**
  ```sh
  QT_QPA_PLATFORM=offscreen python3 -m novaos_desktop --selftest --screenshot out.png
  ```

## License

MIT — see [../LICENSE](../LICENSE).
