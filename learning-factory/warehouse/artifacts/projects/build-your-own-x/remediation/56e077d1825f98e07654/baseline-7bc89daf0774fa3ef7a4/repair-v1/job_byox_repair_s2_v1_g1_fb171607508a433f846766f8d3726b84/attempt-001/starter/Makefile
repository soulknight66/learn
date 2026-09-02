CROSS_COMPILE ?= arm-none-eabi-
CC := $(CROSS_COMPILE)gcc
OBJCOPY := $(CROSS_COMPILE)objcopy

CPPFLAGS := -Iinclude
CFLAGS := -std=c11 -mcpu=arm926ej-s -marm -ffreestanding -fno-builtin \
	-fno-stack-protector -fno-pic -Wall -Wextra -Werror -O2 \
	-ffunction-sections -fdata-sections
ASFLAGS := $(CFLAGS)
LDFLAGS := -nostdlib -Wl,-T,arch/arm/linker.ld -Wl,--gc-sections \
	-Wl,--build-id=none -Wl,-z,noexecstack -Wl,-Map,build/kernel.map

C_SOURCES := kernel/main.c kernel/scheduler.c kernel/vm.c kernel/ramfs.c \
	kernel/runtime.c kernel/uart.c arch/arm/mmu.c
S_SOURCES := arch/arm/start.S arch/arm/context.S
OBJECTS := $(patsubst %.c,build/%.o,$(C_SOURCES)) \
	$(patsubst %.S,build/%.o,$(S_SOURCES))

.PHONY: all clean

all: build/kernel.elf build/kernel.bin

build/kernel.elf: $(OBJECTS) arch/arm/linker.ld
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) $(LDFLAGS) $(OBJECTS) -o $@

build/kernel.bin: build/kernel.elf
	$(OBJCOPY) -O binary $< $@

build/%.o: %.c
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

build/%.o: %.S
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(ASFLAGS) -c $< -o $@

clean:
	rm -rf build
