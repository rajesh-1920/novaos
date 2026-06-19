/*
 * nova/font.h - 8x8 bitmap font (basic Latin, U+0000..U+007F).
 *
 * The glyph table is defined in kernel/src/console/font8x8.c (vendored,
 * public domain). Each glyph is 8 bytes (one per row); within a row the
 * least-significant bit is the leftmost pixel.
 */
#ifndef NOVA_FONT_H
#define NOVA_FONT_H

#define FONT_WIDTH  8
#define FONT_HEIGHT 8
#define FONT_GLYPHS 128

extern const unsigned char font8x8_basic[FONT_GLYPHS][FONT_HEIGHT];

#endif /* NOVA_FONT_H */
