// SPDX-License-Identifier: MIT
// Copyright (c) 2026 rajesh_1920
/*
 * shell/shell.c - NovaOS interactive shell (read-eval-print loop).
 *
 * Input comes from either the PS/2 keyboard or the serial port, so the same
 * shell works in the QEMU window and over a serial console. Output goes to
 * both sinks via kprintf().
 */
#include <nova/shell.h>
#include <nova/keyboard.h>
#include <nova/serial.h>
#include <nova/console.h>
#include <nova/printf.h>
#include <nova/kernel.h>
#include <nova/types.h>
#include <nova/io.h>
#include <nova/cpu.h>

#define LINE_MAX 128

static bool str_eq(const char *a, const char *b)
{
    while (*a != '\0' && *b != '\0') {
        if (*a != *b) {
            return false;
        }
        a++;
        b++;
    }
    return *a == '\0' && *b == '\0';
}

/* If `s` begins with `prefix`, return true and point *rest at the remainder. */
static bool starts_with(const char *s, const char *prefix, const char **rest)
{
    while (*prefix != '\0') {
        if (*s != *prefix) {
            return false;
        }
        s++;
        prefix++;
    }
    if (rest != NULL) {
        *rest = s;
    }
    return true;
}

/* Block until a character arrives from the keyboard or the serial port. */
static char read_char(void)
{
    char c;
    for (;;) {
        if (kbd_try_getchar(&c)) {
            return c;
        }
        if (serial_try_getchar(&c)) {
            if (c == '\r') {
                c = '\n';            /* terminals send CR for Enter   */
            } else if (c == 0x7F) {
                c = '\b';            /* terminals send DEL for Backspace */
            }
            return c;
        }
        __asm__ volatile ("pause"); /* be nice to the (virtual) CPU */
    }
}

static void cmd_help(void)
{
    kprintf("Available commands:\n");
    kprintf("  help          show this help\n");
    kprintf("  about         what NovaOS is\n");
    kprintf("  version       kernel version\n");
    kprintf("  echo <text>   print <text> back\n");
    kprintf("  clear         clear the screen\n");
    kprintf("  reboot        restart the machine\n");
}

static void cmd_reboot(void)
{
    kprintf("rebooting...\n");
    /* Pulse the i8042 CPU-reset line once the input buffer is clear. */
    while (inb(0x64) & 0x02) {
        /* wait */
    }
    outb(0x64, 0xFE);
    cpu_hang();                      /* in case the reset doesn't take */
}

static void execute(char *line)
{
    while (*line == ' ') {           /* skip leading spaces */
        line++;
    }
    if (*line == '\0') {
        return;                      /* empty line */
    }

    const char *rest;
    if (str_eq(line, "help")) {
        cmd_help();
    } else if (str_eq(line, "about")) {
        kprintf("%s v%s - a small hobby OS in C, booted by Limine on x86_64.\n",
                NOVA_NAME, NOVA_VERSION);
        kprintf("You're typing into the kernel's own shell (polled PS/2 + serial).\n");
    } else if (str_eq(line, "version")) {
        kprintf("%s %s\n", NOVA_NAME, NOVA_VERSION);
    } else if (str_eq(line, "clear")) {
        console_clear();
    } else if (starts_with(line, "echo ", &rest)) {
        kprintf("%s\n", rest);
    } else if (str_eq(line, "echo")) {
        kprintf("\n");
    } else if (str_eq(line, "reboot")) {
        cmd_reboot();
    } else {
        kprintf("unknown command: '%s'  (try 'help')\n", line);
    }
}

void shell_run(void)
{
    char line[LINE_MAX];

    kprintf("\nInteractive shell ready. Type 'help' and press Enter.\n");

    for (;;) {
        kprintf("nova> ");

        usize len = 0;
        for (;;) {
            char c = read_char();

            if (c == '\n') {
                console_put_char('\n');
                serial_write_char('\n');
                break;
            }
            if (c == '\b') {
                if (len > 0) {
                    len--;
                    console_put_char('\b');   /* erases on the framebuffer */
                    serial_write("\b \b");    /* erases in the terminal    */
                }
                continue;
            }
            if ((unsigned char)c < 0x20) {
                continue;                     /* ignore other control chars */
            }
            if (len < LINE_MAX - 1) {
                line[len++] = c;
                console_put_char(c);          /* echo to screen */
                serial_write_char(c);         /* echo to serial */
            }
        }

        line[len] = '\0';
        execute(line);
    }
}
