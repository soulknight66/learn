include ../../environment/toolchain.mk

HOST_FLAGS := -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Iinclude
CROSS_FLAGS := -std=gnu11 -O2 -Wall -Wextra -Werror -ffreestanding \
	-fno-builtin -fno-stack-protector -ffunction-sections -fdata-sections \
	-mcpu=cortex-a53 -mgeneral-regs-only -Iinclude
REFERENCE_SOURCES := src/process.c src/vm.c src/ramfs.c
CROSS_OBJECTS := build/aarch64/boot.o build/aarch64/kernel.o \
	build/aarch64/process.o build/aarch64/vm.o build/aarch64/ramfs.o

.PHONY: all test adversarial cross qemu-test clean

all: test adversarial qemu-test

build/host build/aarch64:
	mkdir -p $@

build/host/reference_tests: $(REFERENCE_SOURCES) ../reference_tests/test_reference.c include/minios.h | build/host
	$(HOST_CC) $(HOST_BINUTILS_PREFIX) $(HOST_FLAGS) $(REFERENCE_SOURCES) ../reference_tests/test_reference.c -o $@

build/host/adversarial_tests: $(REFERENCE_SOURCES) ../reference_tests/test_adversarial.c include/minios.h | build/host
	$(HOST_CC) $(HOST_BINUTILS_PREFIX) $(HOST_FLAGS) $(REFERENCE_SOURCES) ../reference_tests/test_adversarial.c -o $@

test: build/host/reference_tests
	./build/host/reference_tests

adversarial: build/host/adversarial_tests
	./build/host/adversarial_tests

build/aarch64/boot.o: baremetal/boot.S | build/aarch64
	$(AARCH64_CC) $(CROSS_FLAGS) -c $< -o $@

build/aarch64/kernel.o: baremetal/kernel.c include/minios.h | build/aarch64
	$(AARCH64_CC) $(CROSS_FLAGS) -c $< -o $@

build/aarch64/process.o: src/process.c include/minios.h | build/aarch64
	$(AARCH64_CC) $(CROSS_FLAGS) -c $< -o $@

build/aarch64/vm.o: src/vm.c include/minios.h | build/aarch64
	$(AARCH64_CC) $(CROSS_FLAGS) -c $< -o $@

build/aarch64/ramfs.o: src/ramfs.c include/minios.h | build/aarch64
	$(AARCH64_CC) $(CROSS_FLAGS) -c $< -o $@

build/aarch64/minios.elf: $(CROSS_OBJECTS) baremetal/linker.ld
	$(AARCH64_CC) -nostdlib -Wl,--build-id=none -Wl,--gc-sections \
		-Wl,-T,baremetal/linker.ld $(CROSS_OBJECTS) -o $@

cross: build/aarch64/minios.elf

qemu-test: build/aarch64/minios.elf
	env LD_LIBRARY_PATH=$(QEMU_GLIB_DIR) $(QEMU_AARCH64) \
		-machine virt -cpu cortex-a53 -smp 1 -m 128M -nographic \
		-monitor none -serial stdio -no-reboot \
		-semihosting-config enable=on,target=native \
		-kernel build/aarch64/minios.elf > build/aarch64/qemu.log 2>&1
	grep -F "MINIOS: PASS" build/aarch64/qemu.log

clean:
	rm -f build/host/reference_tests build/host/adversarial_tests
	rm -f $(CROSS_OBJECTS) build/aarch64/minios.elf build/aarch64/qemu.log
	rmdir build/host build/aarch64 build 2>/dev/null || true
