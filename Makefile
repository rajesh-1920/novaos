# NovaOS - top-level build.
#
# Quick start:
#   make deps      # once: fetch & build the Limine bootloader
#   make run       # build the kernel + ISO and boot it in QEMU
#
# Run `make help` for the full target list.

ARCH    := x86_64
NAME    := novaos

# --- directories ----------------------------------------------------------
BUILD      := build
OBJ_DIR    := $(BUILD)/obj
ISO_ROOT   := $(BUILD)/iso_root
DEPS_DIR   := deps
LIMINE_DIR := $(DEPS_DIR)/limine

KERNEL := $(BUILD)/kernel.elf
ISO    := $(BUILD)/$(NAME).iso

# --- toolchain ------------------------------------------------------------
# clang is a cross-compiler out of the box (no GCC cross-toolchain needed);
# we just point it at a bare-metal target triple.
CC := clang
LD := ld

CFLAGS := \
	-target $(ARCH)-unknown-none-elf \
	-std=gnu11 -Wall -Wextra \
	-ffreestanding -nostdlibinc \
	-fno-stack-protector -fno-stack-check \
	-fno-lto -fno-PIC \
	-ffunction-sections -fdata-sections \
	-m64 -march=x86-64 -mabi=sysv \
	-mno-80387 -mno-mmx -mno-sse -mno-sse2 \
	-mno-red-zone -mcmodel=kernel \
	-O2 -g -pipe \
	-Ikernel/include \
	-MMD -MP

LDFLAGS := \
	-m elf_x86_64 \
	-nostdlib -static \
	-z max-page-size=0x1000 \
	--gc-sections \
	-T kernel/linker/$(ARCH).ld

# --- sources --------------------------------------------------------------
SRCS     := $(shell find kernel/src -name '*.c')
OBJS     := $(patsubst kernel/src/%.c,$(OBJ_DIR)/%.o,$(SRCS))
DEPFILES := $(OBJS:.o=.d)

# --- emulator -------------------------------------------------------------
QEMU      := qemu-system-x86_64
QEMUFLAGS := -M q35 -m 512M -serial stdio -no-reboot

.PHONY: all kernel deps iso run run-uefi clean distclean help

all: $(KERNEL)
kernel: $(KERNEL)

# Compile each .c into build/obj, mirroring the source tree layout.
$(OBJ_DIR)/%.o: kernel/src/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

# Link the freestanding kernel ELF.
$(KERNEL): $(OBJS)
	@mkdir -p $(dir $@)
	$(LD) $(LDFLAGS) $(OBJS) -o $@
	@echo "==> Built $@"

# Fetch + build Limine (one-time; re-run `make deps` to update).
deps: $(DEPS_DIR)/.stamp
$(DEPS_DIR)/.stamp:
	sh scripts/get-deps.sh
	@touch $@

# Stage an ISO tree and master a hybrid BIOS+UEFI bootable image.
iso: $(ISO)
$(ISO): $(KERNEL) $(DEPS_DIR)/.stamp boot/limine.conf
	rm -rf $(ISO_ROOT)
	mkdir -p $(ISO_ROOT)/boot/limine $(ISO_ROOT)/EFI/BOOT
	cp $(KERNEL) $(ISO_ROOT)/boot/kernel
	cp boot/limine.conf $(ISO_ROOT)/boot/limine/
	cp $(LIMINE_DIR)/limine-bios.sys \
	   $(LIMINE_DIR)/limine-bios-cd.bin \
	   $(LIMINE_DIR)/limine-uefi-cd.bin $(ISO_ROOT)/boot/limine/
	cp $(LIMINE_DIR)/BOOTX64.EFI $(LIMINE_DIR)/BOOTIA32.EFI $(ISO_ROOT)/EFI/BOOT/
	xorriso -as mkisofs -R -r -J \
	  -b boot/limine/limine-bios-cd.bin \
	  -no-emul-boot -boot-load-size 4 -boot-info-table \
	  -hfsplus -apm-block-size 2048 \
	  --efi-boot boot/limine/limine-uefi-cd.bin \
	  -efi-boot-part --efi-boot-image \
	  --protective-msdos-label \
	  $(ISO_ROOT) -o $(ISO)
	$(LIMINE_DIR)/limine bios-install $(ISO)
	@echo "==> Built $(ISO)"

# Boot the ISO in QEMU using the legacy BIOS path (simplest, no firmware needed).
run: $(ISO)
	$(QEMU) $(QEMUFLAGS) -cdrom $(ISO) -boot d

# Boot via UEFI; downloads OVMF firmware into deps/ovmf on first use.
run-uefi: $(ISO) $(DEPS_DIR)/ovmf/ovmf-code-x86_64.fd
	$(QEMU) $(QEMUFLAGS) \
	  -drive if=pflash,unit=0,format=raw,file=$(DEPS_DIR)/ovmf/ovmf-code-x86_64.fd,readonly=on \
	  -cdrom $(ISO) -boot d

$(DEPS_DIR)/ovmf/ovmf-code-x86_64.fd:
	mkdir -p $(DEPS_DIR)/ovmf
	curl -L https://github.com/osdev0/edk2-ovmf-stable-bins/releases/latest/download/edk2-ovmf-bins.tar.gz \
	  | gunzip | tar -xf - -C $(DEPS_DIR)/ovmf

clean:
	rm -rf $(BUILD)

distclean: clean
	rm -rf $(DEPS_DIR)

help:
	@echo "NovaOS make targets:"
	@echo "  make deps      Fetch & build the Limine bootloader (run once)"
	@echo "  make           Compile and link the kernel  -> $(KERNEL)"
	@echo "  make iso       Build a bootable ISO          -> $(ISO)"
	@echo "  make run       Boot the ISO in QEMU (BIOS)"
	@echo "  make run-uefi  Boot the ISO in QEMU (UEFI/OVMF)"
	@echo "  make clean     Remove build artifacts"
	@echo "  make distclean Also remove fetched dependencies"

-include $(DEPFILES)
