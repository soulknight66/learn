CROSS ?= aarch64-none-elf-
CC := $(CROSS)gcc
OBJCOPY := $(CROSS)objcopy
CFLAGS := -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror \
	-ffreestanding -fno-stack-protector -fno-pie -mcpu=cortex-a53
LDFLAGS := -nostdlib -nostartfiles -Wl,--build-id=none -T linker.ld

BUILD := build
ELF := $(BUILD)/kernel8.elf
IMAGE := $(BUILD)/kernel8.img

.PHONY: all clean

all: $(IMAGE)

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/boot.o: boot.S | $(BUILD)
	$(CC) $(CFLAGS) -c boot.S -o $@

$(BUILD)/kernel.o: kernel.c | $(BUILD)
	$(CC) $(CFLAGS) -c kernel.c -o $@

$(ELF): $(BUILD)/boot.o $(BUILD)/kernel.o linker.ld
	$(CC) $(LDFLAGS) $(BUILD)/boot.o $(BUILD)/kernel.o -o $@

$(IMAGE): $(ELF)
	$(OBJCOPY) -O binary $(ELF) $(IMAGE)

clean:
	rm -rf $(BUILD)
