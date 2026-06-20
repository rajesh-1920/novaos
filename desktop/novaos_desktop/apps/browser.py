# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Browser - a web browser for NovaOS Desktop.

If Qt WebEngine (Chromium) is installed it is used for full pages. Otherwise the
app falls back to a built-in "lite" engine (urllib + QTextBrowser) that fetches
real pages over HTTP(S) and renders a simplified, JavaScript-free view. Both
modes share the same chrome: back / forward / reload / home, an address bar
that doubles as a search box, and a home page.
"""
import urllib.parse
import urllib.request

from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QTextBrowser, Qt, QUrl, QImage,
)

USER_AGENT = "Mozilla/5.0 (X11; NovaOS Desktop) lite-browser"
HOME = "nova://home"
SEARCH = "https://html.duckduckgo.com/html/?q="

# Detect a real engine, matching whichever Qt binding is active.
HAVE_WEBENGINE = False
try:  # PyQt5
    from PyQt5.QtWebEngineWidgets import QWebEngineView  # type: ignore
    HAVE_WEBENGINE = True
except Exception:
    try:  # PySide6
        from PySide6.QtWebEngineWidgets import QWebEngineView  # type: ignore
        HAVE_WEBENGINE = True
    except Exception:
        HAVE_WEBENGINE = False


HOME_HTML = """
<body style="font-family:sans-serif; color:#e5e9f0;">
  <div style="text-align:center; margin-top:40px;">
    <h1 style="color:#7aa2f7;">NovaOS Browser</h1>
    <p>Type a URL or a search in the address bar above.</p>
    <p style="margin-top:24px; font-size:15px;">
      <a href="https://example.com">example.com</a> &nbsp;&middot;&nbsp;
      <a href="https://en.wikipedia.org/wiki/Operating_system">Wikipedia: OS</a> &nbsp;&middot;&nbsp;
      <a href="https://html.duckduckgo.com/html/?q=NovaOS">Search the web</a> &nbsp;&middot;&nbsp;
      <a href="https://github.com/rajesh-1920/novaos">NovaOS on GitHub</a>
    </p>
  </div>
</body>
"""


def normalize(text: str) -> str:
    """Turn address-bar text into a URL (or a web search)."""
    text = text.strip()
    if not text or text in ("home", HOME):
        return HOME
    if text.startswith(("http://", "https://", "nova://")):
        return text
    if " " not in text and "." in text:
        return "https://" + text
    return SEARCH + urllib.parse.quote(text)


class _LiteView(QTextBrowser):
    """QTextBrowser that can also fetch remote images for rendered pages."""

    def __init__(self):
        super().__init__()
        self.setOpenLinks(False)            # we handle navigation ourselves
        self._cache: dict[str, bytes] = {}

    def loadResource(self, rtype, url):
        u = url.toString()
        if u.startswith(("http://", "https://")):
            try:
                data = self._cache.get(u)
                if data is None:
                    req = urllib.request.Request(u, headers={"User-Agent": USER_AGENT})
                    data = urllib.request.urlopen(req, timeout=8).read()
                    self._cache[u] = data
                img = QImage()
                img.loadFromData(data)
                return img
            except Exception:
                return QImage()
        return super().loadResource(rtype, url)


class Browser(QWidget):
    def __init__(self):
        super().__init__()
        self._history: list[str] = []
        self._index = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        bar = QHBoxLayout()
        self.back_btn = QPushButton("←")
        self.fwd_btn = QPushButton("→")
        self.reload_btn = QPushButton("↻")
        self.home_btn = QPushButton("⌂")
        for b in (self.back_btn, self.fwd_btn, self.reload_btn, self.home_btn):
            b.setFixedWidth(38)
            bar.addWidget(b)
        self.address = QLineEdit()
        self.address.setPlaceholderText("Search or enter address")
        self.address.returnPressed.connect(self._go)
        bar.addWidget(self.address, 1)
        self.go_btn = QPushButton("Go")
        bar.addWidget(self.go_btn)
        layout.addLayout(bar)

        self.back_btn.clicked.connect(self.back)
        self.fwd_btn.clicked.connect(self.forward)
        self.reload_btn.clicked.connect(self.reload)
        self.home_btn.clicked.connect(lambda: self.navigate(HOME))
        self.go_btn.clicked.connect(self._go)

        if HAVE_WEBENGINE:
            self.mode = "webengine"
            self.view = QWebEngineView()
            self.view.urlChanged.connect(
                lambda u: self.address.setText("" if u.toString() == "about:blank" else u.toString()))
            layout.addWidget(self.view, 1)
        else:
            self.mode = "lite"
            self.view = _LiteView()
            self.view.anchorClicked.connect(self._on_anchor)
            layout.addWidget(self.view, 1)
            note = QLabel("Lite mode — no JavaScript. "
                          "Install PyQtWebEngine for full pages.")
            note.setStyleSheet("color:#8a93a8; font-size:11px;")
            layout.addWidget(note)

        self.navigate(HOME)

    # -- navigation ---------------------------------------------------------
    def _current(self) -> str:
        if 0 <= self._index < len(self._history):
            return self._history[self._index]
        return HOME

    def navigate(self, url: str, push: bool = True):
        url = normalize(url)
        if push:
            self._history = self._history[: self._index + 1]
            self._history.append(url)
            self._index = len(self._history) - 1
        self.address.setText("" if url == HOME else url)
        self._show(url)
        self._update_buttons()

    def _show(self, url: str):
        if self.mode == "webengine":
            # QWebEngineView.setHtml() accepts a base URL.
            if url == HOME:
                self.view.setHtml(HOME_HTML, QUrl("nova://home/"))
            else:
                self.view.load(QUrl(url))
            return

        # lite mode: QTextBrowser.setHtml() takes only the html string, so the
        # base URL (for resolving relative links/images) goes on the document.
        if url == HOME:
            self.view.document().setBaseUrl(QUrl("nova://home/"))
            self.view.setHtml(HOME_HTML)
            return
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            resp = urllib.request.urlopen(req, timeout=10)
            charset = resp.headers.get_content_charset() or "utf-8"
            html = resp.read().decode(charset, errors="replace")
            self.view.document().setBaseUrl(QUrl(url))
            self.view.setHtml(html)
        except Exception as exc:
            self.view.setHtml(
                f"<body style='font-family:sans-serif;color:#e5e9f0;'>"
                f"<h2>Could not load page</h2><p>{url}</p>"
                f"<pre style='color:#f7768e;'>{exc}</pre></body>")

    def _go(self):
        text = self.address.text().strip()
        if text:
            self.navigate(text)

    def _on_anchor(self, qurl):
        u = qurl.toString()
        if not u:
            return
        if "://" not in u and not u.startswith("nova:"):
            u = urllib.parse.urljoin(self._current(), u)
        self.navigate(u)

    def back(self):
        if self.mode == "webengine":
            self.view.back()
            return
        if self._index > 0:
            self._index -= 1
            url = self._current()
            self.address.setText("" if url == HOME else url)
            self._show(url)
            self._update_buttons()

    def forward(self):
        if self.mode == "webengine":
            self.view.forward()
            return
        if self._index < len(self._history) - 1:
            self._index += 1
            url = self._current()
            self.address.setText("" if url == HOME else url)
            self._show(url)
            self._update_buttons()

    def reload(self):
        if self.mode == "webengine":
            self.view.reload()
        else:
            self._show(self._current())

    def _update_buttons(self):
        if self.mode == "webengine":
            return
        self.back_btn.setEnabled(self._index > 0)
        self.fwd_btn.setEnabled(self._index < len(self._history) - 1)
