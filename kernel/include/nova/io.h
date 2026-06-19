/* SPDX-License-Identifier: MIT */
/* Copyright (c) 2026 rajesh_1920 */
/*
 * nova/io.h - x86 port-mapped I/O (the `in`/`out` instructions).
 *
 * Used by drivers that talk to legacy hardware over I/O ports, e.g. the
 * 16550 UART (serial console).
 */
#ifndef NOVA_IO_H
#define NOVA_IO_H

#include <nova/types.h>

static inline void outb(u16 port, u8 value)
{
    __asm__ volatile ("outb %0, %1" : : "a"(value), "Nd"(port));
}

static inline u8 inb(u16 port)
{
    u8 value;
    __asm__ volatile ("inb %1, %0" : "=a"(value) : "Nd"(port));
    return value;
}

/* A short, harmless delay by writing to an unused port (POST code port). */
static inline void io_wait(void)
{
    outb(0x80, 0);
}

#endif /* NOVA_IO_H */
