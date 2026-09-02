CC ?= cc
PYTHON ?= python3
CROSS_COMPILE ?= arm-none-eabi-
ARM_CC := $(CROSS_COMPILE)gcc
QEMU ?= qemu-system-arm
QEMU_LD_LIBRARY_PATH ?=
REFERENCE ?= ../reference
BUILD_DIR := build
TARGET := $(BUILD_DIR)/test_reference
ARM_TARGET := $(BUILD_DIR)/runtime_reentrancy.elf

CPPFLAGS := -I$(REFERENCE)/include
CFLAGS := -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic
SANITIZERS ?= -fsanitize=address,undefined -fno-omit-frame-pointer
SOURCES := test_reference.c $(REFERENCE)/kernel/scheduler.c \
	$(REFERENCE)/kernel/vm.c $(REFERENCE)/kernel/ramfs.c
ARM_SOURCES := runtime_reentrancy.c $(REFERENCE)/kernel/scheduler.c \
	$(REFERENCE)/kernel/runtime.c $(REFERENCE)/kernel/uart.c \
	$(REFERENCE)/arch/arm/start.S $(REFERENCE)/arch/arm/context.S
ARM_CPPFLAGS := -I$(REFERENCE)/include
ARM_CFLAGS := -std=c11 -mcpu=arm926ej-s -marm -ffreestanding -fno-builtin \
	-fno-stack-protector -fno-pic -Wall -Wextra -Werror -O2 \
	-ffunction-sections -fdata-sections
ARM_LDFLAGS := -nostdlib -Wl,-T,$(REFERENCE)/arch/arm/linker.ld \
	-Wl,--gc-sections -Wl,--build-id=none -Wl,-z,noexecstack \
	-Wl,-Map,$(BUILD_DIR)/runtime_reentrancy.map

.PHONY: all test arm-test clean

all: $(TARGET)

$(TARGET): $(SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANITIZERS) $(SOURCES) -o $@

test: $(TARGET)
	./$(TARGET)

$(ARM_TARGET): $(ARM_SOURCES) $(REFERENCE)/arch/arm/linker.ld
	@mkdir -p $(BUILD_DIR)
	$(ARM_CC) $(ARM_CPPFLAGS) $(ARM_CFLAGS) $(ARM_LDFLAGS) \
		$(ARM_SOURCES) -o $@

arm-test: $(ARM_TARGET)
	$(PYTHON) run_runtime_qemu.py --qemu $(QEMU) --kernel $(ARM_TARGET) \
		--library-path=$(QEMU_LD_LIBRARY_PATH) --timeout 10

clean:
	rm -rf $(BUILD_DIR)
