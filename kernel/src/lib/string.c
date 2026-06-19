// SPDX-License-Identifier: MIT
// Copyright (c) 2026 rajesh_1920
/*
 * lib/string.c - Freestanding implementations of the memory/string helpers.
 *
 * These are deliberately simple and correct rather than fast. The compiler is
 * allowed to lower things like struct copies into calls to memcpy/memset, so
 * these symbols must exist with exactly these signatures.
 */
#include <nova/string.h>

void *memcpy(void *dest, const void *src, usize n)
{
    u8 *d = (u8 *)dest;
    const u8 *s = (const u8 *)src;
    for (usize i = 0; i < n; i++) {
        d[i] = s[i];
    }
    return dest;
}

void *memset(void *dest, int value, usize n)
{
    u8 *d = (u8 *)dest;
    for (usize i = 0; i < n; i++) {
        d[i] = (u8)value;
    }
    return dest;
}

void *memmove(void *dest, const void *src, usize n)
{
    u8 *d = (u8 *)dest;
    const u8 *s = (const u8 *)src;

    if (d == s || n == 0) {
        return dest;
    }

    if (d < s) {
        /* Forward copy is safe when dest is below src. */
        for (usize i = 0; i < n; i++) {
            d[i] = s[i];
        }
    } else {
        /* Overlap with dest above src: copy backwards. */
        for (usize i = n; i != 0; i--) {
            d[i - 1] = s[i - 1];
        }
    }
    return dest;
}

int memcmp(const void *a, const void *b, usize n)
{
    const u8 *pa = (const u8 *)a;
    const u8 *pb = (const u8 *)b;
    for (usize i = 0; i < n; i++) {
        if (pa[i] != pb[i]) {
            return (int)pa[i] - (int)pb[i];
        }
    }
    return 0;
}

usize strlen(const char *s)
{
    usize len = 0;
    while (s[len] != '\0') {
        len++;
    }
    return len;
}
