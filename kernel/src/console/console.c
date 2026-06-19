// SPDX-License-Identifier: MIT
// Copyright (c) 2026 rajesh_1920
/*
 * console/console.c - Text console on top of the framebuffer.
 *
 * Renders 8x8 glyphs scaled by SCALE, keeps a character-cell cursor, wraps at
 * the right margin, and scrolls the framebuffer when the bottom is reached.
 * Handles \n, \r, \t and \b; other control characters are ignored.
 */
#include <nova/console.h>
#include <nova/framebuffer.h>
#include <nova/font.h>

#define SCALE   2
#define CELL_W  (FONT_WIDTH  * SCALE)
#define CELL_H  (FONT_HEIGHT * SCALE)
#define TAB_STOP 4

static u32  fg_color = 0x00FFFFFF;
static u32  bg_color = 0x00000000;
static u32  cols, rows;          /* console size in character cells */
static u32  cur_col, cur_row;    /* cursor position in cells        */
static bool initialized = false;

static void draw_glyph(char c, u32 col, u32 row)
{
    unsigned char uc = (unsigned char)c;
    if (uc >= FONT_GLYPHS) {
        uc = '?';
    }
    const unsigned char *glyph = font8x8_basic[uc];

    u32 ox = col * CELL_W;
    u32 oy = row * CELL_H;

    for (u32 gy = 0; gy < FONT_HEIGHT; gy++) {
        unsigned char bits = glyph[gy];
        for (u32 gx = 0; gx < FONT_WIDTH; gx++) {
            /* LSB is the leftmost pixel for this font. */
            u32 color = ((bits >> gx) & 1u) ? fg_color : bg_color;
            for (u32 sy = 0; sy < SCALE; sy++) {
                for (u32 sx = 0; sx < SCALE; sx++) {
                    fb_put_pixel(ox + gx * SCALE + sx, oy + gy * SCALE + sy, color);
                }
            }
        }
    }
}

void console_init(u32 fg, u32 bg)
{
    const struct framebuffer *f = fb_get();
    fg_color = fg;
    bg_color = bg;
    cols = f->width  / CELL_W;
    rows = f->height / CELL_H;
    if (cols == 0) cols = 1;
    if (rows == 0) rows = 1;
    cur_col = 0;
    cur_row = 0;
    initialized = true;
    console_clear();
}

void console_set_colors(u32 fg, u32 bg)
{
    fg_color = fg;
    bg_color = bg;
}

void console_clear(void)
{
    fb_clear(bg_color);
    cur_col = 0;
    cur_row = 0;
}

static void newline(void)
{
    cur_col = 0;
    if (cur_row + 1 >= rows) {
        fb_scroll_up(CELL_H, bg_color);
        cur_row = rows - 1;
    } else {
        cur_row++;
    }
}

void console_put_char(char c)
{
    if (!initialized) {
        return;
    }

    switch (c) {
    case '\n':
        newline();
        return;
    case '\r':
        cur_col = 0;
        return;
    case '\t':
        do {
            draw_glyph(' ', cur_col, cur_row);
            cur_col++;
            if (cur_col >= cols) {
                newline();
                return;
            }
        } while (cur_col % TAB_STOP != 0);
        return;
    case '\b':
        if (cur_col > 0) {
            cur_col--;
            draw_glyph(' ', cur_col, cur_row);
        }
        return;
    default:
        break;
    }

    if ((unsigned char)c < 0x20) {
        return;                      /* ignore other control characters */
    }

    draw_glyph(c, cur_col, cur_row);
    cur_col++;
    if (cur_col >= cols) {
        newline();
    }
}

void console_write(const char *s)
{
    if (!initialized) {
        return;
    }
    while (*s != '\0') {
        console_put_char(*s++);
    }
}
