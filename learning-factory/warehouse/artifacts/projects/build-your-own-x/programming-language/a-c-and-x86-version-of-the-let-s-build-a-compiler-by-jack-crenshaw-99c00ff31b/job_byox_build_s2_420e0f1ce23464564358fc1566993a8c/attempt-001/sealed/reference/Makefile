CC ?= cc
CFLAGS ?= -std=c11 -O2 -g
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L
WARNINGS = -Wall -Wextra -Wpedantic -Werror

.PHONY: all clean test

all: pebble

pebble: main.o pebble.o
	$(CC) $(CFLAGS) $(WARNINGS) main.o pebble.o -o $@

%.o: %.c pebble.h
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNINGS) -c $< -o $@

test: pebble
	PEBBLE_BIN=$(CURDIR)/pebble python3 ../reference_tests/run_tests.py

clean:
	rm -f main.o pebble.o pebble
