/* SPDX-License-Identifier: MIT */
/* Copyright (c) 2026 rajesh_1920 */
/*
 * nova/string.h - Freestanding memory/string helpers.
 *
 * The compiler may emit implicit calls to memcpy/memset/memmove/memcmp (e.g.
 * for struct assignments or array initialisers), so the kernel MUST provide
 * them itself. They are defined in kernel/src/lib/string.c.
 */
#ifndef NOVA_STRING_H
#define NOVA_STRING_H

#include <nova/types.h>

void  *memcpy(void *dest, const void *src, usize n);
void  *memset(void *dest, int value, usize n);
void  *memmove(void *dest, const void *src, usize n);
int    memcmp(const void *a, const void *b, usize n);

usize  strlen(const char *s);

#endif /* NOVA_STRING_H */
