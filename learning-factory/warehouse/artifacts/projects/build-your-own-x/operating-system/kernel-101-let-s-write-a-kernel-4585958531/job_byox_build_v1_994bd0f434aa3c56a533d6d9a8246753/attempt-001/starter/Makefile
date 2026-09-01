CC ?= cc
LD ?= ld

BUILD_DIR := build
CORE_SOURCES := src/frames.c src/scheduler.c src/vm.c src/ramfs.c
KERNEL_SOURCES := $(CORE_SOURCES) src/console.c src/kernel.c
KERNEL_OBJECTS := $(patsubst src/%.c,$(BUILD_DIR)/%.o,$(KERNEL_SOURCES))
CFLAGS_COMMON := -std=c11 -Wall -Wextra -Werror -pedantic -Iinclude
CFLAGS_32 := $(CFLAGS_COMMON) -m32 -ffreestanding -fno-pie -fno-stack-protector

.PHONY: all kernel host-check clean

all: host-check

host-check:
	$(CC) $(CFLAGS_COMMON) -ffreestanding -fsyntax-only $(KERNEL_SOURCES)

kernel: $(BUILD_DIR)/tinykernel.elf

$(BUILD_DIR)/tinykernel.elf: $(BUILD_DIR)/boot.o $(KERNEL_OBJECTS) boot/linker.ld
	$(LD) -m elf_i386 --build-id=none -T boot/linker.ld -o $@ $(BUILD_DIR)/boot.o $(KERNEL_OBJECTS)

$(BUILD_DIR)/boot.o: boot/boot.S
	mkdir -p $(BUILD_DIR)
	$(CC) -m32 -ffreestanding -fno-pie -c $< -o $@

$(BUILD_DIR)/%.o: src/%.c include/tinykernel.h
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS_32) -c $< -o $@

clean:
	rm -rf $(BUILD_DIR)
