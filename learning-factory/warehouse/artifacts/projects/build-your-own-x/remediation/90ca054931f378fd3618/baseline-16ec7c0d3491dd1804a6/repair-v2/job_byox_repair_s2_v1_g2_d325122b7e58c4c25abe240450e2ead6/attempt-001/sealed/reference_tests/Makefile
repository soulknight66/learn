PINNED_CC := /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
PINNED_BINUTILS_DIR := /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin
ifeq ($(origin CC),default)
CC := $(if $(wildcard $(PINNED_CC)),$(PINNED_CC),cc)
endif
BINUTILS_DIR ?= $(PINNED_BINUTILS_DIR)
TOOLCHAIN_FLAGS = $(if $(strip $(BINUTILS_DIR)),-B$(patsubst %/,%,$(strip $(BINUTILS_DIR)))/)

REFERENCE := ../reference
CPPFLAGS := -I$(REFERENCE)/include
CFLAGS := -std=c17 -O2 -g -Wall -Wextra -Werror -pedantic
TARGET := build/test_vm

.PHONY: all clean

all: $(TARGET)

$(TARGET): test_vm.c $(REFERENCE)/build/vm.o
	mkdir -p build
	$(CC) $(TOOLCHAIN_FLAGS) $(CPPFLAGS) $(CFLAGS) test_vm.c $(REFERENCE)/build/vm.o -o $@

clean:
	rm -f $(TARGET)
