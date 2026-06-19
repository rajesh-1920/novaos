/* SPDX-License-Identifier: MIT */
/* Copyright (c) 2026 rajesh_1920 */
/*
 * nova/printf.h - Minimal formatted output for the kernel.
 *
 * kprintf() formats its arguments and writes the result to every active log
 * sink (the on-screen console and the serial port). The k*snprintf() helpers
 * format into a caller-provided buffer with the usual snprintf return value
 * (the number of characters that *would* have been written).
 *
 * Supported conversions: %c %s %d %i %u %x %X %p %%
 * Length modifiers:       l  ll  z
 * Flags / width:          '0' zero-pad and a decimal minimum field width,
 *                         e.g. "%016llx".
 */
#ifndef NOVA_PRINTF_H
#define NOVA_PRINTF_H

#include <nova/types.h>
#include <stdarg.h>

int  kvsnprintf(char *buf, usize size, const char *fmt, va_list ap);
int  ksnprintf(char *buf, usize size, const char *fmt, ...)
        __attribute__((format(printf, 3, 4)));

void kprintf(const char *fmt, ...)
        __attribute__((format(printf, 1, 2)));

#endif /* NOVA_PRINTF_H */
