// SPDX-License-Identifier: MIT
// Copyright (c) 2026 rajesh_1920
/*
 * drivers/serial.c - 16550 UART driver for COM1.
 *
 * Configured for 115200 baud, 8 data bits, no parity, 1 stop bit (8N1).
 * Newlines are expanded to CR+LF so output looks correct in a terminal.
 */
#include <nova/serial.h>
#include <nova/io.h>

#define COM1 0x3F8

/* Register offsets from the port base. */
#define REG_DATA        0   /* DLAB=0: data; DLAB=1: divisor low  */
#define REG_INT_ENABLE  1   /* DLAB=0: int enable; DLAB=1: divisor high */
#define REG_FIFO_CTRL   2   /* write: FIFO control                */
#define REG_LINE_CTRL   3   /* line control (DLAB lives here)     */
#define REG_MODEM_CTRL  4   /* modem control                      */
#define REG_LINE_STATUS 5   /* line status                        */
#define REG_SCRATCH     7   /* scratch register (presence probe)  */

#define LINE_STATUS_THR_EMPTY 0x20  /* transmit holding register empty */

static bool initialized = false;

bool serial_init(void)
{
    outb(COM1 + REG_INT_ENABLE, 0x00);  /* disable interrupts          */
    outb(COM1 + REG_LINE_CTRL,  0x80);  /* enable DLAB (set baud rate) */
    outb(COM1 + REG_DATA,       0x01);  /* divisor low  = 1 (115200)   */
    outb(COM1 + REG_INT_ENABLE, 0x00);  /* divisor high = 0            */
    outb(COM1 + REG_LINE_CTRL,  0x03);  /* 8 bits, no parity, 1 stop   */
    outb(COM1 + REG_FIFO_CTRL,  0xC7);  /* enable+clear FIFO, 14-byte  */
    outb(COM1 + REG_MODEM_CTRL, 0x0F);  /* DTR/RTS/OUT1/OUT2, normal   */

    /* Presence probe via the scratch register. Unlike a loopback test this
     * never touches the receive path, so it can't swallow an incoming byte
     * (QEMU drops chardev input while loopback mode is enabled). We mark the
     * port initialised regardless: on a real PC / QEMU COM1 always exists. */
    initialized = true;
    outb(COM1 + REG_SCRATCH, 0xAB);
    return inb(COM1 + REG_SCRATCH) == 0xAB;
}

static void put_raw(char c)
{
    while ((inb(COM1 + REG_LINE_STATUS) & LINE_STATUS_THR_EMPTY) == 0) {
        /* spin until the transmitter is ready */
    }
    outb(COM1 + REG_DATA, (u8)c);
}

void serial_write_char(char c)
{
    if (!initialized) {
        return;
    }
    if (c == '\n') {
        put_raw('\r');
    }
    put_raw(c);
}

void serial_write(const char *s)
{
    if (!initialized) {
        return;
    }
    while (*s != '\0') {
        serial_write_char(*s++);
    }
}

#define LINE_STATUS_DATA_READY 0x01

bool serial_try_getchar(char *out)
{
    if (!initialized) {
        return false;
    }
    if ((inb(COM1 + REG_LINE_STATUS) & LINE_STATUS_DATA_READY) == 0) {
        return false;
    }
    *out = (char)inb(COM1 + REG_DATA);
    return true;
}
