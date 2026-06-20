// SPDX-License-Identifier: MIT
// Copyright (c) 2026 rajesh_1920
/*
 * main.c - NovaOS kernel entry point and boot bring-up.
 *
 * This is the only translation unit that talks to the Limine boot protocol.
 * It declares the requests Limine fills in before jumping to kmain(), then
 * brings up the kernel's subsystems in order and prints a banner:
 *
 *     serial -> framebuffer -> console -> banner -> idle (hlt loop)
 *
 * Limine has already put us in 64-bit long mode with paging enabled and the
 * kernel mapped at the higher-half address from the linker script, so there is
 * no assembly stub to write here.
 */
#include <limine.h>

#include <nova/kernel.h>
#include <nova/types.h>
#include <nova/cpu.h>
#include <nova/serial.h>
#include <nova/framebuffer.h>
#include <nova/console.h>
#include <nova/printf.h>
#include <nova/keyboard.h>
#include <nova/shell.h>

/* --- Limine requests -----------------------------------------------------
 * Each lives in the .limine_requests section (see the linker script) and must
 * be `volatile` and marked `used` so the bootloader can find it and the linker
 * does not garbage-collect it. */

__attribute__((used, section(".limine_requests")))
static volatile uint64_t limine_base_revision[] = LIMINE_BASE_REVISION(6);

__attribute__((used, section(".limine_requests")))
static volatile struct limine_framebuffer_request framebuffer_request = {
    .id = LIMINE_FRAMEBUFFER_REQUEST_ID,
    .revision = 0,
};

/* Start/end markers that delimit the request list for the bootloader. */
__attribute__((used, section(".limine_requests_start")))
static volatile uint64_t limine_requests_start_marker[] = LIMINE_REQUESTS_START_MARKER;

__attribute__((used, section(".limine_requests_end")))
static volatile uint64_t limine_requests_end_marker[] = LIMINE_REQUESTS_END_MARKER;

/* NovaOS colour scheme (0x00RRGGBB). */
#define COLOR_BG     0x001A1B26   /* deep navy   */
#define COLOR_FG     0x00C0CAF5   /* soft white  */
#define COLOR_ACCENT 0x007AA2F7   /* accent blue */

/* --- top-level logging / panic ------------------------------------------ */

void klog(const char *fmt, ...)
{
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    kvsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    kprintf("[nova] %s", buf);
}

void kpanic(const char *fmt, ...)
{
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    kvsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);

    console_set_colors(0x00F7768E, COLOR_BG);   /* red foreground */
    kprintf("\n*** KERNEL PANIC: %s ***\n", buf);
    cpu_hang();
}

/* --- kernel entry point -------------------------------------------------- */

void kmain(void)
{
    /* Serial first: it works even if graphics never come up. */
    serial_init();
    serial_write("\n[nova] serial console online\n");

    /* Verify the bootloader honoured the base revision we asked for. */
    if (!LIMINE_BASE_REVISION_SUPPORTED(limine_base_revision)) {
        serial_write("[nova] FATAL: unsupported Limine base revision\n");
        cpu_hang();
    }

    /* We must have a framebuffer to draw the console. */
    if (framebuffer_request.response == NULL ||
        framebuffer_request.response->framebuffer_count < 1) {
        serial_write("[nova] FATAL: no framebuffer from bootloader\n");
        cpu_hang();
    }

    struct limine_framebuffer *fb = framebuffer_request.response->framebuffers[0];

    if (!fb_init(fb->address, (u32)fb->width, (u32)fb->height,
                 (u32)fb->pitch, (u16)fb->bpp)) {
        serial_write("[nova] FATAL: unsupported framebuffer format\n");
        cpu_hang();
    }

    console_init(COLOR_FG, COLOR_BG);

    /* Banner. */
    console_set_colors(COLOR_ACCENT, COLOR_BG);
    console_write("    _   __                 ____  _____\n");
    console_write("   / | / /___ _   ______ _/ __ \\/ ___/\n");
    console_write("  /  |/ / __ \\ | / / __ `/ / / /\\__ \\ \n");
    console_write(" / /|  / /_/ / |/ / /_/ / /_/ /___/ / \n");
    console_write("/_/ |_/\\____/|___/\\__,_/\\____//____/  \n\n");
    console_set_colors(COLOR_FG, COLOR_BG);

    kprintf("Welcome to %s v%s\n", NOVA_NAME, NOVA_VERSION);
    kprintf("Booted via the Limine boot protocol on x86_64.\n\n");
    kprintf("Framebuffer : %ux%u, %u bpp\n",
            (unsigned)fb->width, (unsigned)fb->height, (unsigned)fb->bpp);
    kprintf("Kernel base : %p\n", (void *)kmain);

    klog("boot complete; starting interactive shell.\n");

    /* Hand off to the shell: an interactive read-eval-print loop driven by the
     * polled keyboard and serial port. It never returns. */
    kbd_init();
    shell_run();

    cpu_hang();   /* safety net, should be unreachable */
}
