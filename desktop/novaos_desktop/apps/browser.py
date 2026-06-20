# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Browser - a web browser for NovaOS Desktop.

If Qt WebEngine (Chromium) is installed it is used for full pages. Otherwise the
app falls back to a built-in "lite" engine (urllib + QTextBrowser) that fetches
real pages over HTTP(S) and renders a simplified, JavaScript-free view.

The lite engine is built for responsiveness:
  * pages are fetched on a background thread, so the desktop never freezes;
  * gzip/deflate transfer encoding is requested (smaller, faster downloads);
  * a page's images are prefetched concurrently into a cache before rendering,
    so QTextBrowser never blocks the GUI thread fetching a resource;
  * visited pages and images are kept in an in-memory LRU cache, making
    back/forward and revisits instant.
"""
import gzip
import re
import threading
import urllib.parse
import urllib.request
import zlib
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QTextBrowser, Qt, QUrl, QImage, Signal,
)

USER_AGENT = "Mozilla/5.0 (X11; NovaOS Desktop) lite-browser"
HOME = "nova://home"
SEARCH = "https://html.duckduckgo.com/html/?q="

PAGE_TIMEOUT = 12          # seconds for the main document
IMAGE_TIMEOUT = 6          # seconds per image
MAX_IMAGES = 16            # images prefetched per page
IMAGE_MAX_BYTES = 3_000_000
PAGE_CACHE_MAX = 40        # LRU size for fetched HTML
IMAGE_CACHE_MAX = 200      # LRU size for fetched images
IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']?([^"\'> ]+)', re.IGNORECASE)

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


def _decompress(raw: bytes, encoding: str) -> bytes:
    encoding = (encoding or "").lower()
    if "gzip" in encoding:
        try:
            return gzip.decompress(raw)
        except OSError:
            return raw
    if "deflate" in encoding:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            try:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
            except zlib.error:
                return raw
    return raw


def _fetch(url: str, timeout: int, limit: int | None = None):
    """Fetch a URL, transparently decompressing gzip/deflate. Returns (bytes, headers)."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate"},
    )
    resp = urllib.request.urlopen(req, timeout=timeout)
    raw = resp.read(limit) if limit else resp.read()
    return _decompress(raw, resp.headers.get("Content-Encoding", "")), resp.headers


class _LiteView(QTextBrowser):
    """QTextBrowser that serves images from a cache only (never blocks to fetch)."""

    def __init__(self, image_cache):
        super().__init__()
        self.setOpenLinks(False)            # navigation is handled by Browser
        self._images = image_cache          # shared LRU dict: url -> bytes

    def loadResource(self, rtype, url):
        u = url.toString()
        if u.startswith(("http://", "https://")):
            data = self._images.get(u)
            if data is None:
                return QImage()             # not prefetched: skip, don't block
            img = QImage()
            img.loadFromData(data)
            return img
        return super().loadResource(rtype, url)


class Browser(QWidget):
    # Emitted from the loader thread; delivered (queued) on the GUI thread.
    _loaded = Signal(int, str, str)         # req_id, url, html
    _failed = Signal(int, str, str)         # req_id, url, error

    def __init__(self):
        super().__init__()
        self._history: list[str] = []
        self._index = -1
        self._req_id = 0
        self._page_cache: "OrderedDict[str, str]" = OrderedDict()
        self._image_cache: "OrderedDict[str, bytes]" = OrderedDict()

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
            self.status = None
        else:
            self.mode = "lite"
            self.view = _LiteView(self._image_cache)
            self.view.anchorClicked.connect(self._on_anchor)
            layout.addWidget(self.view, 1)
            self.status = QLabel("Lite mode — pages load in the background.")
            self.status.setStyleSheet("color:#8a93a8; font-size:11px;")
            layout.addWidget(self.status)
            self._loaded.connect(self._on_loaded)
            self._failed.connect(self._on_failed)

        self.navigate(HOME)

    # -- caches -------------------------------------------------------------
    def _cache_page(self, url, html):
        self._page_cache[url] = html
        self._page_cache.move_to_end(url)
        while len(self._page_cache) > PAGE_CACHE_MAX:
            self._page_cache.popitem(last=False)

    def _cache_image(self, url, data):
        self._image_cache[url] = data
        self._image_cache.move_to_end(url)
        while len(self._image_cache) > IMAGE_CACHE_MAX:
            self._image_cache.popitem(last=False)

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
        self._load(url)
        self._update_buttons()

    def _load(self, url: str):
        if self.mode == "webengine":
            if url == HOME:
                self.view.setHtml(HOME_HTML, QUrl("nova://home/"))
            else:
                self.view.load(QUrl(url))
            return

        # lite mode
        if url == HOME:
            self._render(url, HOME_HTML)
            self._set_status("Ready.")
            return

        cached = self._page_cache.get(url)
        if cached is not None:
            self._page_cache.move_to_end(url)
            self._render(url, cached)
            self._set_status("Loaded from cache.")
            return

        # Fetch on a background thread so the UI stays responsive.
        self._req_id += 1
        rid = self._req_id
        self._set_status("Loading…")
        threading.Thread(target=self._worker, args=(rid, url), daemon=True).start()

    def _worker(self, rid: int, url: str):
        try:
            raw, headers = _fetch(url, PAGE_TIMEOUT)
            charset = headers.get_content_charset() or "utf-8"
            html = raw.decode(charset, errors="replace")
            self._prefetch_images(html, url)
            self._loaded.emit(rid, url, html)
        except Exception as exc:                       # noqa: BLE001
            self._failed.emit(rid, url, str(exc))

    def _prefetch_images(self, html: str, base_url: str):
        wanted = []
        for src in IMG_SRC_RE.findall(html):
            if src.startswith("data:"):
                continue
            u = urllib.parse.urljoin(base_url, src)
            if u.startswith(("http://", "https://")) and u not in self._image_cache:
                wanted.append(u)
            if len(wanted) >= MAX_IMAGES:
                break
        if not wanted:
            return

        def grab(u):
            try:
                data, _ = _fetch(u, IMAGE_TIMEOUT, limit=IMAGE_MAX_BYTES)
                return u, data
            except Exception:                          # noqa: BLE001
                return u, None

        with ThreadPoolExecutor(max_workers=6) as pool:
            for u, data in pool.map(grab, wanted):
                if data:
                    self._cache_image(u, data)

    def _on_loaded(self, rid: int, url: str, html: str):
        if rid != self._req_id:
            return                                     # a newer request won
        self._cache_page(url, html)
        self._render(url, html)
        self._set_status("Done.")

    def _on_failed(self, rid: int, url: str, error: str):
        if rid != self._req_id:
            return
        self._render(url,
                     f"<body style='font-family:sans-serif;color:#e5e9f0;'>"
                     f"<h2>Could not load page</h2><p>{url}</p>"
                     f"<pre style='color:#f7768e;'>{error}</pre></body>")
        self._set_status("Failed to load.")

    def _render(self, url: str, html: str):
        """Render html in the lite view, with a base URL for relative resources."""
        base = "nova://home/" if url == HOME else url
        self.view.document().setBaseUrl(QUrl(base))
        self.view.setHtml(html)

    def _set_status(self, text: str):
        if self.status is not None:
            self.status.setText(text)

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
            self._load(url)
            self._update_buttons()

    def forward(self):
        if self.mode == "webengine":
            self.view.forward()
            return
        if self._index < len(self._history) - 1:
            self._index += 1
            url = self._current()
            self.address.setText("" if url == HOME else url)
            self._load(url)
            self._update_buttons()

    def reload(self):
        if self.mode == "webengine":
            self.view.reload()
            return
        self._page_cache.pop(self._current(), None)    # force a fresh fetch
        self._load(self._current())

    def _update_buttons(self):
        if self.mode == "webengine":
            return
        self.back_btn.setEnabled(self._index > 0)
        self.fwd_btn.setEnabled(self._index < len(self._history) - 1)
