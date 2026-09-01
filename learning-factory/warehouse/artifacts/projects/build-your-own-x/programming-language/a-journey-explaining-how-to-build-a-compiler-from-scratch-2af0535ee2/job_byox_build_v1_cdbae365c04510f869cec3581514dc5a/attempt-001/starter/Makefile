CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
CPPFLAGS ?= -Iinclude
BUILD := build
OBJECTS := $(BUILD)/main.o $(BUILD)/pebble.o

.PHONY: all clean test

all: $(BUILD)/pebble

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/main.o: src/main.c include/pebble.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c src/main.c -o $@

$(BUILD)/pebble.o: src/pebble.c include/pebble.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c src/pebble.c -o $@

$(BUILD)/pebble: $(OBJECTS)
	$(CC) $(CFLAGS) $(OBJECTS) -o $@

test: all
	PEBBLE_BIN=$(CURDIR)/$(BUILD)/pebble python3 ../public_tests/test_cli.py

clean:
	rm -f $(OBJECTS) $(BUILD)/pebble
