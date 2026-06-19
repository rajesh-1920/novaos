# NovaOS Roadmap

NovaOS is built milestone by milestone. Each one is small, ends in something you
can see working, and lays groundwork for the next. Tackle them in order.

### ✅ Milestone 1 — Boot & output (done)
- Boot via Limine into 64-bit long mode.
- Serial (COM1) log + framebuffer text console.
- `kprintf`, a tiny freestanding string lib, a banner.

### Milestone 2 — CPU tables & interrupts
- **GDT**: load a flat 64-bit Global Descriptor Table (`kernel/src/arch/x86_64/gdt.c`).
- **IDT**: install an Interrupt Descriptor Table and CPU exception handlers
  (divide-by-zero, page fault, …) that print a register dump via `kpanic`.
- **PIC/APIC**: remap the legacy PIC (or set up the Local APIC) and unmask IRQs.
- *Visible result:* trigger an exception on purpose and see a clean panic.

### Milestone 3 — Timer & keyboard (interactive)
- **PIT or APIC timer**: a periodic tick; print a heartbeat.
- **PS/2 keyboard** driver on IRQ1: translate scancodes to ASCII.
- A minimal line editor → the start of a shell.
- *Visible result:* type into NovaOS and echo characters back.

### Milestone 4 — Physical & virtual memory
- **Physical frame allocator** from Limine's memory map (add a
  `limine_memmap_request` in `main.c`).
- **Paging**: manage your own page tables; map/unmap pages.
- **Kernel heap**: a simple `kmalloc`/`kfree` (bump or free-list).
- *Visible result:* dynamic allocation works; print the memory map.

### Milestone 5 — Multitasking
- **Tasks/threads** with a context switch (save/restore registers).
- **Scheduler**: cooperative first, then preemptive on the timer IRQ.
- *Visible result:* two tasks printing concurrently.

### Milestone 6 — Userspace & syscalls
- Ring 3 execution, a `syscall`/`sysret` entry, a tiny syscall table.
- Load a flat user program (embedded as a Limine module to start).

### Milestone 7 — Filesystem & storage
- A RAM disk + a read-only filesystem (e.g. a tar/initrd or FAT reader).
- Wire it behind a small VFS so the shell can `ls`/`cat`.

## Conventions for new code
- New CPU/arch code goes under `kernel/src/arch/x86_64/`; add the dir to the
  build automatically (the Makefile already globs `kernel/src/**.c`).
- Every module gets a header in `kernel/include/nova/` with a top comment
  describing its job.
- Keep `main.c` as the *only* file that includes `limine.h`; expose new boot
  info (memory map, modules, RSDP) through small init functions it calls.
- Prefer adding a `nova/*.h` API over reaching into another module's internals.

## Handy references
- Limine protocol & config: <https://github.com/limine-bootloader/limine>
- OSDev wiki: <https://wiki.osdev.org>
- Intel SDM (architecture reference) for GDT/IDT/paging details.
