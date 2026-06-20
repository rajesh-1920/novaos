/* SPDX-License-Identifier: MIT */
/* Copyright (c) 2026 rajesh_1920 */
/*
 * nova/serial.h - 16550 UART driver (COM1), used as a debug log sink.
 *
 * Serial output is invaluable for OS development: it works before any graphics
 * are up, survives crashes, and can be captured by QEMU with `-serial stdio`.
 */
#ifndef NOVA_SERIAL_H
#define NOVA_SERIAL_H

#include <nova/types.h>

/* Initialise COM1 (115200 8N1). Returns true if the loopback self-test passes. */
bool serial_init(void);

void serial_write_char(char c);
void serial_write(const char *s);

/* Non-blocking receive: if a byte has arrived on COM1, store it in *out and
 * return true; otherwise return false. Lets the shell be driven over serial. */
bool serial_try_getchar(char *out);

#endif /* NOVA_SERIAL_H */
