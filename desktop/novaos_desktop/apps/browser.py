# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Browser - a web browser for NovaOS Desktop.

If Qt WebEngine (Chromium) is installed it is used for full pages. Otherwise the
app falls back to a built-in "lite" engine (urllib + QTextBrowser) that fetches
real pages over HTTP(S) and renders a simplified, JavaScript-free view.

The lite engine is built for responsiveness:
  * pages are fetched on a background thread, so the desktop never freezes;
  * the text renders immediately (fast first paint); images are then fetched
    concurrently in the background and filled in, instead of holding the page;
  * HTTP keep-alive connection pooling via requests (when available) avoids a
    fresh TLS handshake per resource; gzip/deflate transfers are negotiated;
  * <script>/<style>/<svg> are stripped for much faster QTextBrowser layout;
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
from html import escape as _esc, unescape as _unesc

from ..qt import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QTextBrowser, Qt, QUrl, QImage, Signal,
)
from .network import is_online

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
MAX_HTML = 1_500_000       # cap the document size handed to QTextBrowser
_STRIP_RE = re.compile(
    r"<(script|style|svg|noscript|iframe)\b.*?</\1>|<!--.*?-->",
    re.IGNORECASE | re.DOTALL)
# DuckDuckGo HTML-endpoint result parsing.
_RESULT_A_RE = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                          re.IGNORECASE | re.DOTALL)
_SNIPPET_RE = re.compile(r'class="result__snippet"[^>]*>(.*?)</a>',
                         re.IGNORECASE | re.DOTALL)
_TAG_RE = re.compile(r"<[^>]+>")

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


OFFLINE_HTML = """
<body style="font-family:sans-serif; color:#e5e9f0;">
  <div style="text-align:center; margin-top:50px;">
    <h2 style="color:#f7768e;">You are offline</h2>
    <p>NovaOS Desktop's Wi-Fi is off or disconnected.</p>
    <p>Open the <b>Network</b> app and turn Wi-Fi on / connect, then try again.</p>
    <p style="color:#8a93a8; font-size:12px;">(This is NovaOS's own network switch —
       your computer's real Wi-Fi is unaffected.)</p>
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


# Prefer a pooled requests.Session (keep-alive) when available; fall back to
# urllib. Pooling avoids a new TCP+TLS handshake for every image on a page.
try:
    import requests
    _SESSION = requests.Session()
    _SESSION.headers["User-Agent"] = USER_AGENT
    HAVE_REQUESTS = True
except Exception:
    HAVE_REQUESTS = False


def http_text(url: str, timeout: int) -> str:
    if HAVE_REQUESTS:
        return _SESSION.get(url, timeout=timeout).text
    raw, headers = _fetch(url, timeout)
    return raw.decode(headers.get_content_charset() or "utf-8", errors="replace")


def http_bytes(url: str, timeout: int, max_bytes: int) -> bytes:
    if HAVE_REQUESTS:
        r = _SESSION.get(url, timeout=timeout, stream=True)
        try:
            return r.raw.read(max_bytes, decode_content=True)
        finally:
            r.close()
    raw, _ = _fetch(url, timeout, limit=max_bytes)
    return raw


def _clean_html(html: str) -> str:
    """Strip heavy/irrelevant markup so QTextBrowser lays out fast."""
    html = _STRIP_RE.sub(" ", html)
    if len(html) > MAX_HTML:
        html = html[:MAX_HTML] + "<p style='color:#8a93a8'>… (truncated)</p>"
    return html


def _is_search(url: str) -> bool:
    return url.startswith("https://html.duckduckgo.com/html")


def _ddg_real_url(href: str) -> str:
    """DDG result hrefs are redirects (//duckduckgo.com/l/?uddg=<real>); unwrap them."""
    href = href.replace("&amp;", "&")
    if href.startswith("//"):
        href = "https:" + href
    try:
        params = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
        if "uddg" in params:
            return params["uddg"][0]
    except Exception:                                  # noqa: BLE001
        pass
    return href


def _build_results_page(url: str, raw: str) -> str:
    """Render DuckDuckGo's HTML results as a clean, readable results page."""
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("q", [""])[0]

    def clean(s):
        return _unesc(_TAG_RE.sub("", s)).strip()

    titles = _RESULT_A_RE.findall(raw)
    snippets = _SNIPPET_RE.findall(raw)

    parts = ["<body style='font-family:sans-serif; color:#e5e9f0;'>",
             f"<h2 style='color:#7aa2f7;'>Results for &ldquo;{_esc(query)}&rdquo;</h2>"]
    if not titles:
        parts.append("<p>No results found.</p>")
    for i, (href, title) in enumerate(titles):
        real = _ddg_real_url(href)
        text = clean(title) or real
        snippet = clean(snippets[i]) if i < len(snippets) else ""
        parts.append(
            "<p style='margin:0 0 14px 0;'>"
            f"<a href='{_esc(real)}' style='font-size:15px; color:#7aa2f7;'>{_esc(text)}</a><br>"
            f"<span style='color:#9ece6a; font-size:11px;'>{_esc(real)}</span><br>"
            f"<span>{_esc(snippet)}</span></p>")
    parts.append("</body>")
    return "".join(parts)


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
    _loaded = Signal(int, str, str)         # req_id, url, html (text, first paint)
    _images_ready = Signal(int, str, int)   # req_id, url, n_new_images
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
            self._images_ready.connect(self._on_images_ready)
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
        # NovaOS network gate: if NovaOS Wi-Fi is off, act offline (the host's
        # real connection is irrelevant here).
        if url != HOME and not is_online():
            self._show_offline()
            return

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
            raw = http_text(url, PAGE_TIMEOUT)
            html = _build_results_page(url, raw) if _is_search(url) else _clean_html(raw)
            self._loaded.emit(rid, url, html)          # 1) paint the text now
            n = self._prefetch_images(html, url)       # 2) fetch images (pooled)
            self._images_ready.emit(rid, url, n)       # 3) fill them in
        except Exception as exc:                       # noqa: BLE001
            self._failed.emit(rid, url, str(exc))

    def _prefetch_images(self, html: str, base_url: str) -> int:
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
            return 0

        def grab(u):
            try:
                return u, http_bytes(u, IMAGE_TIMEOUT, IMAGE_MAX_BYTES)
            except Exception:                          # noqa: BLE001
                return u, None

        n = 0
        with ThreadPoolExecutor(max_workers=8) as pool:
            for u, data in pool.map(grab, wanted):
                if data:
                    self._cache_image(u, data)
                    n += 1
        return n

    def _on_loaded(self, rid: int, url: str, html: str):
        if rid != self._req_id:
            return                                     # a newer request won
        self._cache_page(url, html)
        self._render(url, html)
        self._set_status("Loaded — fetching images…")

    def _on_images_ready(self, rid: int, url: str, n_new: int):
        if rid != self._req_id:
            return
        if n_new:
            # Re-render so the now-cached images appear, preserving scroll.
            bar = self.view.verticalScrollBar()
            pos = bar.value()
            self._render(url, self._page_cache.get(url, ""))
            bar.setValue(pos)
        self._set_status("Done.")

    def _on_failed(self, rid: int, url: str, error: str):
        if rid != self._req_id:
            return
        self._render(url,
                     f"<body style='font-family:sans-serif;color:#e5e9f0;'>"
                     f"<h2>Could not load page</h2><p>{url}</p>"
                     f"<pre style='color:#f7768e;'>{error}</pre></body>")
        self._set_status("Failed to load.")

    def _show_offline(self):
        if self.mode == "webengine":
            self.view.setHtml(OFFLINE_HTML, QUrl("nova://offline/"))
        else:
            self.view.document().setBaseUrl(QUrl("nova://offline/"))
            self.view.setHtml(OFFLINE_HTML)
        self._set_status("Offline — enable Wi-Fi in the Network app.")

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
