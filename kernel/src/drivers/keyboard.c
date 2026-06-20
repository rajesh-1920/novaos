// SPDX-License-Identifier: MIT
// Copyright (c) 2026 rajesh_1920
/*
 * drivers/keyboard.c - Polled PS/2 keyboard driver (US QWERTY, scancode set 1).
 *
 * We poll the i8042 status port; when a byte is ready we read the scancode and
 * translate make-codes to ASCII. Release codes (bit 7 set) are ignored except
 * for the shift keys, whose state we track.
 */
#include <nova/keyboard.h>
#include <nova/io.h>

#define PS2_DATA               0x60
#define PS2_STATUS             0x64
#define PS2_STATUS_OUTPUT_FULL 0x01   /* a byte is waiting to be read       */
#define PS2_STATUS_FROM_AUX    0x20   /* byte came from the mouse, not kbd  */

#define SC_LSHIFT 0x2A
#define SC_RSHIFT 0x36
#define SC_RELEASE 0x80               /* bit 7 set = key release            */
#define SC_TABLE_SIZE 0x3A            /* we map make-codes 0x00..0x39       */

/* Scancode set 1 -> ASCII, unshifted. Entries left 0 are unmapped. */
static const char map_lower[SC_TABLE_SIZE] = {
    [0x02]='1',[0x03]='2',[0x04]='3',[0x05]='4',[0x06]='5',
    [0x07]='6',[0x08]='7',[0x09]='8',[0x0A]='9',[0x0B]='0',
    [0x0C]='-',[0x0D]='=',[0x0E]='\b',[0x0F]='\t',
    [0x10]='q',[0x11]='w',[0x12]='e',[0x13]='r',[0x14]='t',
    [0x15]='y',[0x16]='u',[0x17]='i',[0x18]='o',[0x19]='p',
    [0x1A]='[',[0x1B]=']',[0x1C]='\n',
    [0x1E]='a',[0x1F]='s',[0x20]='d',[0x21]='f',[0x22]='g',
    [0x23]='h',[0x24]='j',[0x25]='k',[0x26]='l',[0x27]=';',
    [0x28]='\'',[0x29]='`',[0x2B]='\\',
    [0x2C]='z',[0x2D]='x',[0x2E]='c',[0x2F]='v',[0x30]='b',
    [0x31]='n',[0x32]='m',[0x33]=',',[0x34]='.',[0x35]='/',
    [0x37]='*',[0x39]=' ',
};

/* Scancode set 1 -> ASCII, with Shift held. */
static const char map_upper[SC_TABLE_SIZE] = {
    [0x02]='!',[0x03]='@',[0x04]='#',[0x05]='$',[0x06]='%',
    [0x07]='^',[0x08]='&',[0x09]='*',[0x0A]='(',[0x0B]=')',
    [0x0C]='_',[0x0D]='+',[0x0E]='\b',[0x0F]='\t',
    [0x10]='Q',[0x11]='W',[0x12]='E',[0x13]='R',[0x14]='T',
    [0x15]='Y',[0x16]='U',[0x17]='I',[0x18]='O',[0x19]='P',
    [0x1A]='{',[0x1B]='}',[0x1C]='\n',
    [0x1E]='A',[0x1F]='S',[0x20]='D',[0x21]='F',[0x22]='G',
    [0x23]='H',[0x24]='J',[0x25]='K',[0x26]='L',[0x27]=':',
    [0x28]='"',[0x29]='~',[0x2B]='|',
    [0x2C]='Z',[0x2D]='X',[0x2E]='C',[0x2F]='V',[0x30]='B',
    [0x31]='N',[0x32]='M',[0x33]='<',[0x34]='>',[0x35]='?',
    [0x37]='*',[0x39]=' ',
};

static bool shift_held = false;

void kbd_init(void)
{
    /* Discard anything already sitting in the output buffer. */
    while (inb(PS2_STATUS) & PS2_STATUS_OUTPUT_FULL) {
        (void)inb(PS2_DATA);
    }
}

bool kbd_try_getchar(char *out)
{
    u8 status = inb(PS2_STATUS);
    if (!(status & PS2_STATUS_OUTPUT_FULL)) {
        return false;                 /* nothing to read */
    }

    u8 sc = inb(PS2_DATA);
    if (status & PS2_STATUS_FROM_AUX) {
        return false;                 /* mouse byte: ignore */
    }

    if (sc == SC_LSHIFT || sc == SC_RSHIFT) {
        shift_held = true;
        return false;
    }
    if (sc == (SC_LSHIFT | SC_RELEASE) || sc == (SC_RSHIFT | SC_RELEASE)) {
        shift_held = false;
        return false;
    }
    if (sc & SC_RELEASE) {
        return false;                 /* other key releases: ignore */
    }
    if (sc >= SC_TABLE_SIZE) {
        return false;                 /* keys we don't map (F-keys, etc.) */
    }

    char c = shift_held ? map_upper[sc] : map_lower[sc];
    if (c == 0) {
        return false;
    }
    *out = c;
    return true;
}
