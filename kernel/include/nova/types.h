/*
 * nova/types.h - Fixed-width integer and convenience type aliases.
 *
 * The kernel is freestanding: there is no libc. We rely on the compiler's
 * freestanding headers (stdint.h / stddef.h / stdbool.h) which clang provides
 * even with -nostdlibinc, and add short aliases used throughout NovaOS.
 */
#ifndef NOVA_TYPES_H
#define NOVA_TYPES_H

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

typedef uint8_t  u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;

typedef int8_t   i8;
typedef int16_t  i16;
typedef int32_t  i32;
typedef int64_t  i64;

typedef size_t   usize;   /* pointer-width unsigned (64-bit on x86_64) */

#endif /* NOVA_TYPES_H */
