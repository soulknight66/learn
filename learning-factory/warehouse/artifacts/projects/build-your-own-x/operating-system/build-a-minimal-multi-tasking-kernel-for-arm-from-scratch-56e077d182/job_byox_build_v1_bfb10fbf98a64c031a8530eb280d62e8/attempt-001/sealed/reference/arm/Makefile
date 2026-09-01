CROSS ?= arm-none-eabi-
CC := $(CROSS)gcc
OBJCOPY := $(CROSS)objcopy
CFLAGS := -mcpu=cortex-a15 -marm -ffreestanding -fno-builtin -nostdlib -O2 \
	-ffunction-sections -fdata-sections -Wall -Wextra -Werror
LDFLAGS := -T linker.ld -nostdlib -Wl,--gc-sections -Wl,--build-id=none

.PHONY: all clean run

all: kernel.bin

kernel.elf: start.S context_switch.S kernel_main.c linker.ld
	$(CC) $(CFLAGS) start.S context_switch.S kernel_main.c $(LDFLAGS) -o $@

kernel.bin: kernel.elf
	$(OBJCOPY) -O binary $< $@

run: kernel.bin
	qemu-system-arm -M virt -cpu cortex-a15 -nographic -monitor none -serial stdio -kernel kernel.bin

clean:
	rm -f kernel.elf kernel.bin
