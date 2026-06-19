// SPDX-License-Identifier: MIT
// Copyright (c) 2026 rajesh_1920
/*
 * lib/printf.c - Minimal printf-family for the kernel.
 *
 * A single formatter (kvsnprintf) drives everything. kprintf() formats into a
 * stack buffer and writes the result to the console and the serial port.
 */
#include <nova/printf.h>
#include <nova/string.h>
#include <nova/console.h>
#include <nova/serial.h>

/* Bounded output sink: writes into `buf` (leaving room for a NUL) while always
 * counting how many characters *would* have been produced (snprintf semantics). */
struct out {
    char *buf;
    usize size;
    usize pos;
    usize count;
};

static void out_char(struct out *o, char c)
{
    if (o->buf != NULL && o->pos + 1 < o->size) {
        o->buf[o->pos++] = c;
    }
    o->count++;
}

static void out_str(struct out *o, const char *s)
{
    while (*s != '\0') {
        out_char(o, *s++);
    }
}

/* Format an unsigned integer with optional sign, base, case, and zero/space pad. */
static void out_uint(struct out *o, u64 value, unsigned base, bool upper,
                     bool negative, unsigned width, bool zero_pad)
{
    const char *digits = upper ? "0123456789ABCDEF" : "0123456789abcdef";
    char tmp[32];
    unsigned n = 0;

    if (value == 0) {
        tmp[n++] = '0';
    }
    while (value != 0) {
        tmp[n++] = digits[value % base];
        value /= base;
    }

    unsigned body = n + (negative ? 1u : 0u);

    if (zero_pad) {
        if (negative) {
            out_char(o, '-');
        }
        for (unsigned w = body; w < width; w++) {
            out_char(o, '0');
        }
    } else {
        for (unsigned w = body; w < width; w++) {
            out_char(o, ' ');
        }
        if (negative) {
            out_char(o, '-');
        }
    }

    while (n != 0) {
        out_char(o, tmp[--n]);
    }
}

int kvsnprintf(char *buf, usize size, const char *fmt, va_list ap)
{
    struct out o = { buf, size, 0, 0 };

    for (const char *p = fmt; *p != '\0'; p++) {
        if (*p != '%') {
            out_char(&o, *p);
            continue;
        }

        p++;                        /* skip '%' */
        if (*p == '\0') {
            break;
        }

        bool zero_pad = false;
        while (*p == '0') {          /* the only flag we support */
            zero_pad = true;
            p++;
        }

        unsigned width = 0;
        while (*p >= '0' && *p <= '9') {
            width = width * 10u + (unsigned)(*p - '0');
            p++;
        }

        int length = 0;             /* 0=int, 1=long, 2=long long, 3=size_t */
        if (*p == 'z') {
            length = 3;
            p++;
        } else {
            while (*p == 'l') {
                length++;
                p++;
            }
        }

        char conv = *p;
        switch (conv) {
        case '%':
            out_char(&o, '%');
            break;

        case 'c':
            out_char(&o, (char)va_arg(ap, int));
            break;

        case 's': {
            const char *s = va_arg(ap, const char *);
            if (s == NULL) {
                s = "(null)";
            }
            for (unsigned w = (unsigned)strlen(s); w < width; w++) {
                out_char(&o, ' ');
            }
            out_str(&o, s);
            break;
        }

        case 'd':
        case 'i': {
            i64 v;
            if (length >= 2) {
                v = va_arg(ap, long long);
            } else if (length == 1 || length == 3) {
                v = va_arg(ap, long);
            } else {
                v = va_arg(ap, int);
            }
            bool neg = v < 0;
            /* Magnitude without overflowing on the most-negative value. */
            u64 mag = neg ? (u64)(-(v + 1)) + 1u : (u64)v;
            out_uint(&o, mag, 10, false, neg, width, zero_pad);
            break;
        }

        case 'u':
        case 'x':
        case 'X': {
            u64 v;
            if (length >= 2) {
                v = va_arg(ap, unsigned long long);
            } else if (length == 1) {
                v = va_arg(ap, unsigned long);
            } else if (length == 3) {
                v = va_arg(ap, usize);
            } else {
                v = va_arg(ap, unsigned int);
            }
            out_uint(&o, v, conv == 'u' ? 10 : 16, conv == 'X', false, width, zero_pad);
            break;
        }

        case 'p': {
            u64 v = (u64)(uintptr_t)va_arg(ap, void *);
            out_str(&o, "0x");
            out_uint(&o, v, 16, false, false, width, zero_pad);
            break;
        }

        default:                    /* unknown conversion: print it literally */
            out_char(&o, '%');
            out_char(&o, conv);
            break;
        }
    }

    if (size > 0) {
        usize term = (o.pos < size) ? o.pos : size - 1;
        buf[term] = '\0';
    }
    return (int)o.count;
}

int ksnprintf(char *buf, usize size, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    int n = kvsnprintf(buf, size, fmt, ap);
    va_end(ap);
    return n;
}

void kprintf(const char *fmt, ...)
{
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    kvsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    console_write(buf);
    serial_write(buf);
}
