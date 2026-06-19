# NovaOS

A small, clean, hobby operating system kernel for **x86_64**, written in **C**
and booted with the modern **[Limine](https://github.com/limine-bootloader/limine)**
bootloader. NovaOS boots straight into 64-bit long mode, brings up a serial log
and a framebuffer text console, prints a banner, and idles.

It is built to be *read*: every subsystem is a small, self-contained module with
a clear header, and the build is a single conventional `Makefile`.

```
    _   __                 ____  _____
   / | / /___ _   ______ _/ __ \/ ___/
  /  |/ / __ \ | / / __ `/ / / /\__ \
 / /|  / /_/ / |/ / /_/ / /_/ /___/ /
/_/ |_/\____/|___/\__,_/\____//____/
```

## Quick start

NovaOS builds on a Debian/Kali-style Linux host.

```sh
# 1. Install the tools that aren't preinstalled (clang/ld/nasm/make are assumed).
sudo apt install qemu-system-x86 xorriso

# 2. Fetch & build the Limine bootloader (one time; needs network).
make deps

# 3. Build the kernel + a bootable ISO and run it in QEMU.
make run
```

You should see the NovaOS banner in the QEMU window, and the same boot log on
your terminal (QEMU is launched with `-serial stdio`).

> **Note:** `clang` acts as the cross-compiler via the `x86_64-unknown-none-elf`
> target triple, so there is **no GCC cross-toolchain to build**.

## Make targets

| Command         | What it does                                            |
|-----------------|---------------------------------------------------------|
| `make deps`     | Fetch + build the Limine bootloader (run once)          |
| `make`          | Compile and link the kernel → `build/kernel.elf`        |
| `make iso`      | Build a bootable hybrid BIOS/UEFI ISO → `build/novaos.iso` |
| `make run`      | Boot the ISO in QEMU (BIOS)                             |
| `make run-uefi` | Boot the ISO in QEMU (UEFI, downloads OVMF firmware)    |
| `make clean`    | Remove build artifacts                                  |
| `make distclean`| Also remove fetched dependencies                        |

## Layout

```
novaos/
├── Makefile              # build orchestration
├── boot/limine.conf      # bootloader menu / kernel path
├── scripts/get-deps.sh   # fetches the Limine bootloader
├── docs/                 # ARCHITECTURE.md, ROADMAP.md
└── kernel/
    ├── include/          # public headers (limine.h + nova/*.h)
    ├── linker/x86_64.ld  # higher-half link script
    └── src/
        ├── main.c        # entry point + Limine handshake
        ├── lib/          # string.c, printf.c (freestanding libc bits)
        ├── drivers/      # serial.c, framebuffer.c
        └── console/      # console.c, font8x8.c
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how it all fits together
and [docs/ROADMAP.md](docs/ROADMAP.md) for what to build next.

## Status

Milestone 1 (bootable kernel with on-screen + serial output) — **done**.
NovaOS is an active learning project; the roadmap grows it toward interrupts,
memory management, and multitasking.

## Third-party code

`limine.h` (Limine protocol) and `font8x8` (public-domain bitmap font) are
vendored in-tree. See [THIRD_PARTY.md](THIRD_PARTY.md) for licenses and origins.
