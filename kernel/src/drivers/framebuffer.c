// SPDX-License-Identifier: MIT
// Copyright (c) 2026 rajesh_1920
/*
 * drivers/framebuffer.c - Linear 32-bpp framebuffer drawing primitives.
 *
 * State is kept in a single file-local struct populated by fb_init() from the
 * geometry Limine reports. All drawing is plain pointer arithmetic into the
 * linear buffer; there is no double buffering yet.
 */
#include <nova/framebuffer.h>
#include <nova/string.h>

static struct framebuffer fb;
static bool initialized = false;

bool fb_init(volatile void *address, u32 width, u32 height, u32 pitch, u16 bpp)
{
    if (address == NULL || bpp != 32) {
        return false;               /* we only support 32-bpp framebuffers */
    }

    fb.pixels = (volatile u32 *)address;
    fb.width  = width;
    fb.height = height;
    fb.stride = pitch / 4;          /* bytes-per-line -> pixels-per-line   */
    fb.bpp    = bpp;
    initialized = true;
    return true;
}

const struct framebuffer *fb_get(void)
{
    return &fb;
}

void fb_put_pixel(u32 x, u32 y, u32 color)
{
    if (!initialized || x >= fb.width || y >= fb.height) {
        return;
    }
    fb.pixels[(usize)y * fb.stride + x] = color;
}

void fb_fill_rect(u32 x, u32 y, u32 w, u32 h, u32 color)
{
    if (!initialized) {
        return;
    }
    u32 x_end = x + w < fb.width  ? x + w : fb.width;
    u32 y_end = y + h < fb.height ? y + h : fb.height;

    for (u32 py = y; py < y_end; py++) {
        volatile u32 *row = &fb.pixels[(usize)py * fb.stride];
        for (u32 px = x; px < x_end; px++) {
            row[px] = color;
        }
    }
}

void fb_clear(u32 color)
{
    fb_fill_rect(0, 0, fb.width, fb.height, color);
}

void fb_scroll_up(u32 rows, u32 color)
{
    if (!initialized || rows == 0) {
        return;
    }
    if (rows >= fb.height) {
        fb_clear(color);
        return;
    }

    usize line_bytes = (usize)fb.stride * sizeof(u32);
    usize moved_lines = fb.height - rows;

    /* Shift the visible content up by `rows` scanlines. memmove handles the
     * (here non-overlapping) move; cast away volatile for the bulk copy. */
    memmove((void *)fb.pixels,
            (void *)&fb.pixels[(usize)rows * fb.stride],
            moved_lines * line_bytes);

    /* Clear the freshly exposed rows at the bottom. */
    fb_fill_rect(0, fb.height - rows, fb.width, rows, color);
}
