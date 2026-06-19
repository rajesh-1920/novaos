# NovaOS Architecture

This document explains how NovaOS is put together and how a power-on turns into
the banner on screen. It is intentionally short — the code is the source of
truth, and every module has a header comment.

## Design principles

1. **Small, single-purpose modules.** Each `.c` file owns one concern and
   exposes a tiny header in `kernel/include/nova/`.
2. **The boot protocol is contained.** Only `main.c` includes `limine.h`; the
   rest of the kernel knows nothing about how it was booted.
3. **Freestanding, no libc.** We provide exactly the few libc-style helpers we
   need (`string.c`, `printf.c`). The compiler's freestanding headers supply
   `stdint.h`/`stddef.h`/`stdbool.h`/`stdarg.h`.
4. **Readable build.** One conventional `Makefile`; `clang` is the cross
   compiler via a target triple, so there is no toolchain to bootstrap.

## Boot flow

```
Power on / QEMU
    │
    ▼
Limine bootloader            (BIOS or UEFI; from the ISO)
    │  - enters 64-bit long mode, enables paging
    │  - maps the kernel at 0xffffffff80000000 (higher half)
    │  - fills in our .limine_requests (base revision, framebuffer)
    │  - jumps to the ELF entry symbol: kmain
    ▼
kmain()  (kernel/src/main.c)
    │  1. serial_init()            -> debug log works immediately
    │  2. check base revision + framebuffer response
    │  3. fb_init(...)             -> adopt the linear framebuffer
    │  4. console_init(...)        -> text console on the framebuffer
    │  5. print banner + system info via kprintf()
    │  6. cpu_hang()               -> hlt loop (no scheduler yet)
```

Because Limine does the CPU mode setup, **there is no assembly boot stub** in
NovaOS yet. The only inline assembly is the handful of instruction wrappers in
`nova/cpu.h` and `nova/io.h`.

## The Limine handshake

Limine looks for tagged "requests" in the `.limine_requests` sections. `main.c`
declares three things there, each `volatile` + `used` so they survive
optimization and `--gc-sections`:

- `LIMINE_BASE_REVISION(6)` — the protocol revision we speak.
- a `limine_framebuffer_request` — asks for a linear framebuffer.
- start/end markers that bracket the request list.

The linker script (`kernel/linker/x86_64.ld`) `KEEP()`s those sections and
places the kernel in the higher half, which is what `-mcmodel=kernel` assumes.

## Module map

| Module                         | Responsibility                                  |
|--------------------------------|-------------------------------------------------|
| `kernel/src/main.c`            | Entry point, Limine handshake, `klog`/`kpanic`  |
| `kernel/src/drivers/serial.c`  | 16550 UART (COM1) debug log                      |
| `kernel/src/drivers/framebuffer.c` | Pixel/rect drawing + scrolling on a linear FB |
| `kernel/src/console/console.c` | Text console: glyph drawing, cursor, scrolling   |
| `kernel/src/console/font8x8.c` | Vendored 8x8 bitmap font data                     |
| `kernel/src/lib/string.c`      | `memcpy/memset/memmove/memcmp/strlen`            |
| `kernel/src/lib/printf.c`      | `kvsnprintf`/`ksnprintf`/`kprintf`               |
| `kernel/include/nova/*.h`      | Public headers for the modules above             |
| `kernel/include/nova/cpu.h`    | `hlt`/`cli`/`sti`/`cpu_hang` wrappers            |
| `kernel/include/nova/io.h`     | `inb`/`outb` port I/O                            |

Output sinks (console + serial) are wired together in `kprintf()`: one call
writes to both the screen and the serial line, so logs are visible in QEMU's
window *and* captured on the terminal.

## Memory model (today)

- Single address space, no userspace, single core in use.
- Kernel mapped at `0xffffffff80000000` (higher half).
- No dynamic allocator yet — everything is static or on the stack Limine set up.

These are the first things the [roadmap](ROADMAP.md) replaces.

## Build pipeline

```
kernel/src/**/*.c --clang(freestanding, x86_64-unknown-none-elf)--> build/obj/**/*.o
build/obj/**/*.o   --ld(-T x86_64.ld, higher-half)----------------> build/kernel.elf
kernel.elf + limine binaries + limine.conf --xorriso + limine bios-install--> build/novaos.iso
build/novaos.iso  --qemu-system-x86_64-------------------------------------> running NovaOS
```
