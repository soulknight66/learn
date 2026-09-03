PINNED_CC := /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
ifeq ($(origin CC),default)
CC := $(if $(wildcard $(PINNED_CC)),$(PINNED_CC),cc)
endif

CPPFLAGS := -Iinclude
CFLAGS := -std=c17 -O2 -g -Wall -Wextra -Werror -pedantic
SOURCES := src/main.c src/lexer.c src/compiler.c src/vm.c
OBJECTS := $(SOURCES:src/%.c=build/%.o)
TARGET := build/emberc-ref

.PHONY: all clean

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) $(OBJECTS) -o $@

build/%.o: src/%.c include/ember.h src/internal.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)
