# Third-party code in NovaOS

NovaOS vendors two small external files. Everything else is original.

## 1. Limine protocol header — `kernel/include/limine.h`

- **Project:** Limine bootloader, protocol header.
- **Source:** https://github.com/limine-bootloader/limine-protocol
  (pinned at commit `80ef54bed402b8c0b672a707c1df4c532f3428ad`).
- **License:** 0BSD (BSD Zero Clause — as declared by the file's own SPDX tag).
- **Why vendored:** it is a single self-contained header (only needs
  `<stdint.h>`), so the kernel compiles offline. Only the bootloader *binaries*
  are fetched at build time by `scripts/get-deps.sh`.

## 2. 8x8 bitmap font — `kernel/src/console/font8x8.c`

- **Project:** `font8x8` by Daniel Hepper, based on Marcel Sondaar's and IBM's
  public-domain VGA fonts.
- **Source:** https://github.com/dhepper/font8x8 (`font8x8_basic.h`).
- **License:** Public Domain.
- **Local change:** the array declaration was changed from `char` to
  `const unsigned char` so the glyph table lives in `.rodata`. The data itself
  is verbatim.

## Build-time dependency (not vendored)

`scripts/get-deps.sh` fetches the **Limine bootloader** binary release
(https://github.com/limine-bootloader/limine, BSD-2-Clause) into `deps/`. It is
not committed to this repository.
