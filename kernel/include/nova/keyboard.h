// SPDX-License-Identifier: MIT
// Copyright (c) 2026 rajesh_1920
/*
 * nova/keyboard.h - Polled PS/2 keyboard input.
 *
 * No interrupts yet: we read the i8042 controller directly. This is simple and
 * reliable; an IRQ-driven version is a later milestone.
 */
#ifndef NOVA_KEYBOARD_H
#define NOVA_KEYBOARD_H

#include <nova/types.h>

/* Drain any stale bytes from the controller. */
void kbd_init(void);

/* Non-blocking. If a key press maps to an ASCII character, store it in *out
 * and return true; otherwise return false (no key, a release, a modifier, …). */
bool kbd_try_getchar(char *out);

#endif /* NOVA_KEYBOARD_H */
