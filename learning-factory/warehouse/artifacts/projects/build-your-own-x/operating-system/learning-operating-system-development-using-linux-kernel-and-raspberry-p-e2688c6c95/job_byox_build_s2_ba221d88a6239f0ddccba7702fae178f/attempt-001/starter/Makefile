ifeq ($(origin CC), default)
CC := /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
endif

BASE_CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Iinclude
SOURCES := src/process.c src/vm.c src/ramfs.c
OBJECTS := build/process.o build/vm.o build/ramfs.o

.PHONY: all compile test clean

all: compile

compile: $(OBJECTS)

build:
	mkdir -p build

build/process.o: src/process.c include/minios.h | build
	$(CC) $(BASE_CFLAGS) $(CFLAGS) -c $< -o $@

build/vm.o: src/vm.c include/minios.h | build
	$(CC) $(BASE_CFLAGS) $(CFLAGS) -c $< -o $@

build/ramfs.o: src/ramfs.c include/minios.h | build
	$(CC) $(BASE_CFLAGS) $(CFLAGS) -c $< -o $@

build/public_tests: $(SOURCES) include/minios.h ../public_tests/test_public.c | build
	$(CC) $(BASE_CFLAGS) $(CFLAGS) $(SOURCES) ../public_tests/test_public.c -o $@

test: build/public_tests
	./build/public_tests

clean:
	rm -f $(OBJECTS) build/public_tests
	rmdir build 2>/dev/null || true
