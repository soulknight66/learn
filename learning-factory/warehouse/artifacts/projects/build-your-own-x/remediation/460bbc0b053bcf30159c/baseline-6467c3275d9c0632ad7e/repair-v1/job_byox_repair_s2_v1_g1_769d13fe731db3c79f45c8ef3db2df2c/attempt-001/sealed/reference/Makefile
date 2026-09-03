CC := /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
NASM := /arm/tools/nasm/nasm/2.16.03/rhe8-x86_64/bin/nasm
LD := /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld

HOST_FLAGS := -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
FREESTANDING_FLAGS := -std=c11 -m32 -O2 -Wall -Wextra -Wpedantic -Werror \
	-ffreestanding -fno-builtin -fno-pie -fno-stack-protector \
	-march=i386 -mno-sse -mno-sse2 -mno-mmx
BUILD := build

.PHONY: all host kernel clean

all: host kernel

host: $(BUILD)/demo

kernel: $(BUILD)/cairnos.elf

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/demo: src/demo.c src/cairn.c include/cairn.h | $(BUILD)
	$(CC) $(HOST_FLAGS) -Iinclude src/demo.c src/cairn.c -o $@

$(BUILD)/boot.o: boot/boot.asm | $(BUILD)
	$(NASM) -f elf32 $< -o $@

$(BUILD)/boot_kernel.o: boot/kernel.c include/cairn.h | $(BUILD)
	$(CC) $(FREESTANDING_FLAGS) -Iinclude -c $< -o $@

$(BUILD)/cairn_freestanding.o: src/cairn.c include/cairn.h | $(BUILD)
	$(CC) $(FREESTANDING_FLAGS) -Iinclude -c $< -o $@

$(BUILD)/cairnos.elf: $(BUILD)/boot.o $(BUILD)/boot_kernel.o \
	$(BUILD)/cairn_freestanding.o boot/linker.ld
	$(LD) -m elf_i386 -T boot/linker.ld -o $@ $(BUILD)/boot.o \
		$(BUILD)/boot_kernel.o $(BUILD)/cairn_freestanding.o

clean:
	rm -rf $(BUILD)
