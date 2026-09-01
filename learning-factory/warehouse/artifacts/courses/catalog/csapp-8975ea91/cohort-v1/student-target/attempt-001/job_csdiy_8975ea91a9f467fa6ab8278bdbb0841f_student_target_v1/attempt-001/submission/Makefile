CC ?= cc
PYTHON ?= python3
CPPFLAGS ?=
CFLAGS ?= -O2
LDFLAGS ?=
LDLIBS ?=

STRICT_CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Werror
INCLUDES = -Iinclude
PROGRAM_OBJECTS = build/main.o build/bytehist.o

.PHONY: all test clean

all: build/bytehist

build/bytehist: $(PROGRAM_OBJECTS)
	$(CC) $(LDFLAGS) $^ $(LDLIBS) -o $@

build/main.o: src/main.c include/bytehist.h | build
	$(CC) $(CPPFLAGS) $(CFLAGS) $(STRICT_CFLAGS) $(INCLUDES) -c $< -o $@

build/bytehist.o: src/bytehist.c include/bytehist.h | build
	$(CC) $(CPPFLAGS) $(CFLAGS) $(STRICT_CFLAGS) $(INCLUDES) -c $< -o $@

build/test_bytehist_module: tests/test_bytehist_module.c src/bytehist.c \
                            include/bytehist.h | build
	$(CC) $(CPPFLAGS) $(CFLAGS) $(STRICT_CFLAGS) $(INCLUDES) \
		tests/test_bytehist_module.c src/bytehist.c -o $@

build:
	mkdir -p $@

test: build/bytehist build/test_bytehist_module
	./build/test_bytehist_module
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) tests/test_bytehist.py

clean:
	rm -rf -- build
