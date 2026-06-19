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

#endif /* NOVA_SERIAL_H */
