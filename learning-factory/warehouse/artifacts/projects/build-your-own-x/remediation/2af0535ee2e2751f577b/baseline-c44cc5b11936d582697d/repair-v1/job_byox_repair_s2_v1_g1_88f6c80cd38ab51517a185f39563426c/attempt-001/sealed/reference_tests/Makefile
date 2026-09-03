CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
CPPFLAGS ?= -I../reference/include

BUILD_DIR := build
TARGET := $(BUILD_DIR)/vm_safety

.PHONY: all clean test

all: $(TARGET)

$(TARGET): vm_safety.c ../reference/src/vm.c ../reference/include/sprig.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) vm_safety.c ../reference/src/vm.c -o $@

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

test: all
	$(TARGET)

clean:
	rm -f $(TARGET)
