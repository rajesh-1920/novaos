/* SPDX-License-Identifier: MIT */
/* Copyright (c) 2026 rajesh_1920 */
/*
 * x86_64.ld - Link script for the NovaOS kernel.
 *
 * The kernel is loaded in the higher half (top -2 GiB) which is what
 * -mcmodel=kernel expects. Limine reads the .limine_requests sections to find
 * our boot requests, so they are KEEP()'d and placed first. Each output
 * section gets its own program header with the right load semantics.
 */

OUTPUT_FORMAT(elf64-x86-64)
ENTRY(kmain)

PHDRS
{
    limine_requests PT_LOAD;
    text            PT_LOAD;
    rodata          PT_LOAD;
    data            PT_LOAD;
}

SECTIONS
{
    . = 0xffffffff80000000;

    .limine_requests : {
        KEEP(*(.limine_requests_start))
        KEEP(*(.limine_requests))
        KEEP(*(.limine_requests_end))
    } :limine_requests

    . = ALIGN(CONSTANT(MAXPAGESIZE));

    .text : {
        *(.text .text.*)
    } :text

    . = ALIGN(CONSTANT(MAXPAGESIZE));

    .rodata : {
        *(.rodata .rodata.*)
    } :rodata

    .note.gnu.build-id : {
        *(.note.gnu.build-id)
    } :rodata

    . = ALIGN(CONSTANT(MAXPAGESIZE));

    .data : {
        *(.data .data.*)
    } :data

    /* .bss must stay in the :data segment; otherwise the file would be padded
     * with a large run of zeros for the uninitialised data. */
    .bss : {
        *(.bss .bss.*)
        *(COMMON)
    } :data

    /DISCARD/ : {
        *(.eh_frame*)
        *(.note .note.*)
    }
}
