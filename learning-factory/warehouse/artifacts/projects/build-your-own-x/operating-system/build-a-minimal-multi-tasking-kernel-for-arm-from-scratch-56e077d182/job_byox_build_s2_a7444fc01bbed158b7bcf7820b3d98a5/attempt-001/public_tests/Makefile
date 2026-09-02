CC ?= cc
KERNEL_SRC ?= ../starter
BUILD_DIR := build
TARGET := $(BUILD_DIR)/test_kernel

CPPFLAGS := -I$(KERNEL_SRC)/include
CFLAGS := -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic
SANITIZERS ?= -fsanitize=address,undefined -fno-omit-frame-pointer
SOURCES := test_kernel.c $(KERNEL_SRC)/kernel/scheduler.c \
	$(KERNEL_SRC)/kernel/vm.c $(KERNEL_SRC)/kernel/ramfs.c

.PHONY: all test clean

all: $(TARGET)

$(TARGET): $(SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANITIZERS) $(SOURCES) -o $@

test: $(TARGET)
	./$(TARGET)

clean:
	rm -rf $(BUILD_DIR)
