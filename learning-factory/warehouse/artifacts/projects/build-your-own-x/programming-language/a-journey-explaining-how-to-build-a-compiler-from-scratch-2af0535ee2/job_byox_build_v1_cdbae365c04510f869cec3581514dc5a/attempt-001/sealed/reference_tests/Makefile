CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
REFERENCE := ../reference
BUILD := build

.PHONY: all test clean

all: $(BUILD)/api_test

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/api_test: api_test.c $(REFERENCE)/src/pebble.c $(REFERENCE)/include/pebble.h | $(BUILD)
	$(CC) $(CFLAGS) -I$(REFERENCE)/include api_test.c $(REFERENCE)/src/pebble.c -o $@

test: all
	PEBBLE_BIN=$(PEBBLE_BIN) python3 test_reference.py
	$(BUILD)/api_test

clean:
	rm -f $(BUILD)/api_test
