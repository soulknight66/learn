PINNED_CC := /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
PINNED_BINUTILS_DIR := /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin
ifeq ($(origin CC),default)
CC := $(if $(wildcard $(PINNED_CC)),$(PINNED_CC),cc)
endif
BINUTILS_DIR ?= $(PINNED_BINUTILS_DIR)
TOOLCHAIN_FLAGS = $(if $(strip $(BINUTILS_DIR)),-B$(patsubst %/,%,$(strip $(BINUTILS_DIR)))/)

CPPFLAGS := -Iinclude
CFLAGS := -std=c17 -O2 -g -Wall -Wextra -Werror -pedantic
SOURCES := src/main.c src/lexer.c src/compiler.c src/vm.c
OBJECTS := $(SOURCES:src/%.c=build/%.o)
TARGET := build/emberc

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(TOOLCHAIN_FLAGS) $(CFLAGS) $(OBJECTS) -o $@

build/%.o: src/%.c include/ember.h
	mkdir -p build
	$(CC) $(TOOLCHAIN_FLAGS) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)
