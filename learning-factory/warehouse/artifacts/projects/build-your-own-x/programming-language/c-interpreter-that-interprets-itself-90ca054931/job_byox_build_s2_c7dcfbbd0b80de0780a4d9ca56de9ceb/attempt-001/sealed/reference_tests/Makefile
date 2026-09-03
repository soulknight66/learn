PINNED_CC := /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
ifeq ($(origin CC),default)
CC := $(if $(wildcard $(PINNED_CC)),$(PINNED_CC),cc)
endif

REFERENCE := ../reference
CPPFLAGS := -I$(REFERENCE)/include
CFLAGS := -std=c17 -O2 -g -Wall -Wextra -Werror -pedantic
TARGET := build/test_vm

.PHONY: all clean

all: $(TARGET)

$(TARGET): test_vm.c $(REFERENCE)/build/vm.o
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) test_vm.c $(REFERENCE)/build/vm.o -o $@

clean:
	rm -f $(TARGET)
