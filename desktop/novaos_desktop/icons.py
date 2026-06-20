# SPDX-License-Identifier: MIT
# Copyright (c) 2026 rajesh_1920
"""Programmatically drawn icons.

We render simple rounded-square glyph icons with QPainter instead of shipping
image files, so the app has zero asset dependencies and looks consistent
regardless of the system icon theme or emoji fonts.
"""
from .qt import Qt, QRectF, QIcon, QPixmap, QPainter, QColor, QFont, QBrush


def make_icon(letter: str, color: str, size: int = 48) -> QIcon:
    """A rounded square filled with `color` and a centered white `letter`."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(QColor(color)))
    inset = size * 0.06
    p.drawRoundedRect(QRectF(inset, inset, size - 2 * inset, size - 2 * inset),
                      size * 0.22, size * 0.22)

    p.setPen(QColor("white"))
    font = QFont("Sans Serif", int(size * 0.42))
    font.setBold(True)
    p.setFont(font)
    p.drawText(pm.rect(), Qt.AlignCenter, letter)
    p.end()
    return QIcon(pm)


def make_pixmap(letter: str, color: str, size: int = 48) -> QPixmap:
    return make_icon(letter, color, size).pixmap(size, size)
