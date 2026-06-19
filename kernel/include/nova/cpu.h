/* SPDX-License-Identifier: MIT */
/* Copyright (c) 2026 rajesh_1920 */
/*
 * nova/cpu.h - Thin wrappers over a handful of x86_64 instructions.
 *
 * Everything here is a static inline so it lowers to a single instruction with
 * no call overhead. As NovaOS grows (GDT, IDT, paging) this is where the
 * lowest-level CPU helpers will live.
 */
#ifndef NOVA_CPU_H
#define NOVA_CPU_H

/* Execute one HLT: stop the core until the next interrupt. */
static inline void cpu_halt(void)
{
    __asm__ volatile ("hlt");
}

/* Mask maskable interrupts on this core. */
static inline void cpu_cli(void)
{
    __asm__ volatile ("cli");
}

/* Unmask maskable interrupts on this core. */
static inline void cpu_sti(void)
{
    __asm__ volatile ("sti");
}

/* Halt forever. Used as the kernel's final resting state and on panic. */
__attribute__((noreturn))
static inline void cpu_hang(void)
{
    cpu_cli();
    for (;;) {
        cpu_halt();
    }
}

#endif /* NOVA_CPU_H */
