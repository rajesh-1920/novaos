/* SPDX-License-Identifier: MIT */
/* Copyright (c) 2026 rajesh_1920 */
/*
 * nova/console.h - Text console rendered on the framebuffer.
 *
 * Draws characters from the 8x8 font (optionally scaled), tracks a cursor,
 * wraps at the right edge, and scrolls when the bottom is reached.
 */
#ifndef NOVA_CONSOLE_H
#define NOVA_CONSOLE_H

#include <nova/types.h>

/* Initialise the console with foreground/background colours (0x00RRGGBB).
 * Requires fb_init() to have succeeded first. Clears the screen. */
void console_init(u32 fg, u32 bg);

void console_clear(void);
void console_set_colors(u32 fg, u32 bg);

void console_put_char(char c);
void console_write(const char *s);

#endif /* NOVA_CONSOLE_H */
