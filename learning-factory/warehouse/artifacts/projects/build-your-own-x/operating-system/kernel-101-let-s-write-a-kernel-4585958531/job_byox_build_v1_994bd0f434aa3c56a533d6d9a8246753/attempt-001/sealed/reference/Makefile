CC ?= cc
LD ?= ld

BUILD_DIR := build
CORE_SOURCES := src/frames.c src/scheduler.c src/vm.c src/ramfs.c
CORE_OBJECTS := $(patsubst src/%.c,$(BUILD_DIR)/%.o,$(CORE_SOURCES))
CFLAGS_COMMON := -std=c11 -Wall -Wextra -Werror -pedantic -Iinclude
CFLAGS_32 := $(CFLAGS_COMMON) -m32 -ffreestanding -fno-pie -fno-stack-protector

.PHONY: all host-check kernel clean

all: host-check

host-check:
	$(CC) $(CFLAGS_COMMON) -ffreestanding -fsyntax-only $(CORE_SOURCES)

kernel: $(BUILD_DIR)/tinykernel.elf

$(BUILD_DIR)/tinykernel.elf: $(BUILD_DIR)/boot.o $(CORE_OBJECTS) \
	$(BUILD_DIR)/console.o $(BUILD_DIR)/kernel.o ../../starter/boot/linker.ld
	$(LD) -m elf_i386 --build-id=none -T ../../starter/boot/linker.ld -o $@ \
		$(BUILD_DIR)/boot.o $(CORE_OBJECTS) $(BUILD_DIR)/console.o $(BUILD_DIR)/kernel.o

$(BUILD_DIR)/boot.o: ../../starter/boot/boot.S
	mkdir -p $(BUILD_DIR)
	$(CC) -m32 -ffreestanding -fno-pie -c $< -o $@

$(BUILD_DIR)/console.o: ../../starter/src/console.c
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS_32) -c $< -o $@

$(BUILD_DIR)/kernel.o: ../../starter/src/kernel.c
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS_32) -c $< -o $@

$(BUILD_DIR)/%.o: src/%.c include/tinykernel.h
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS_32) -c $< -o $@

clean:
	rm -rf $(BUILD_DIR)
