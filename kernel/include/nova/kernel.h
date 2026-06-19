/*
 * nova/kernel.h - Core kernel identity and top-level helpers.
 */
#ifndef NOVA_KERNEL_H
#define NOVA_KERNEL_H

#include <nova/types.h>

#define NOVA_NAME    "NovaOS"
#define NOVA_VERSION "0.1.0"

/* Log a message to all sinks (console + serial). Thin wrapper over kprintf
 * that prefixes "[nova] ". Defined in main.c. */
void klog(const char *fmt, ...) __attribute__((format(printf, 1, 2)));

/* Print a message and halt the machine forever. Never returns. */
__attribute__((noreturn))
void kpanic(const char *fmt, ...) __attribute__((format(printf, 1, 2)));

#endif /* NOVA_KERNEL_H */
