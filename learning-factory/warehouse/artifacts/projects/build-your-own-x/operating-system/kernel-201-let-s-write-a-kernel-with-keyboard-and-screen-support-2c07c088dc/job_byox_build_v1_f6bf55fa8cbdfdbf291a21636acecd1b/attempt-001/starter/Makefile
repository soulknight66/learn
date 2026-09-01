CC := gcc
LD := ld
BUILD := build
CPPFLAGS := -Iinclude
CFLAGS := -std=c11 -m32 -ffreestanding -fno-pie -fno-pic -fno-stack-protector \
	-fno-builtin -Wall -Wextra -Werror -O2
ASFLAGS := -m32 -ffreestanding -fno-pie -fno-pic
LDFLAGS := -m elf_i386 -T arch/i386/linker.ld --build-id=none

C_SOURCES := src/kernel.c src/terminal.c src/keyboard.c src/interrupts.c
ASM_SOURCES := arch/i386/boot.S arch/i386/interrupt_stubs.S
C_OBJECTS := $(patsubst src/%.c,$(BUILD)/%.o,$(C_SOURCES))
ASM_OBJECTS := $(patsubst arch/i386/%.S,$(BUILD)/%.o,$(ASM_SOURCES))
OBJECTS := $(ASM_OBJECTS) $(C_OBJECTS)

.PHONY: all kernel test inspect clean

all: kernel

kernel: $(BUILD)/kernel.elf

$(BUILD)/kernel.elf: $(OBJECTS) arch/i386/linker.ld
	$(LD) $(LDFLAGS) -o $@ $(OBJECTS)

$(BUILD)/%.o: src/%.c
	@mkdir -p $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD)/%.o: arch/i386/%.S
	@mkdir -p $(BUILD)
	$(CC) $(ASFLAGS) -c $< -o $@

test:
	$(MAKE) -C ../public_tests PROJECT=../starter run

inspect: kernel
	readelf -h $(BUILD)/kernel.elf
	readelf -S $(BUILD)/kernel.elf
	od -An -tx4 -N12 $(BUILD)/kernel.elf

clean:
	rm -rf $(BUILD)
	$(MAKE) -C ../public_tests clean
