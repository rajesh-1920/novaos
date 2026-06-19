/*
 * nova/framebuffer.h - Linear (32-bpp) framebuffer drawing.
 *
 * Limine hands us a ready-to-use linear framebuffer. The boot code in main.c
 * pulls the address/geometry out of the Limine response and passes the raw
 * values here, so this module never needs to know about the boot protocol.
 *
 * Pixels are 0x00RRGGBB. Only the common 32-bpp case is handled; other depths
 * are rejected by fb_init().
 */
#ifndef NOVA_FRAMEBUFFER_H
#define NOVA_FRAMEBUFFER_H

#include <nova/types.h>

struct framebuffer {
    volatile u32 *pixels;   /* base address of the framebuffer            */
    u32 width;              /* visible width  in pixels                   */
    u32 height;             /* visible height in pixels                   */
    u32 stride;             /* pixels per scanline (pitch / 4)            */
    u16 bpp;                /* bits per pixel (must be 32)                */
};

/* Adopt the Limine-provided framebuffer. `pitch` is in bytes. */
bool fb_init(volatile void *address, u32 width, u32 height, u32 pitch, u16 bpp);

const struct framebuffer *fb_get(void);

void fb_put_pixel(u32 x, u32 y, u32 color);
void fb_fill_rect(u32 x, u32 y, u32 w, u32 h, u32 color);
void fb_clear(u32 color);

/* Scroll the whole framebuffer up by `rows` pixels, backfilling with `color`. */
void fb_scroll_up(u32 rows, u32 color);

#endif /* NOVA_FRAMEBUFFER_H */
