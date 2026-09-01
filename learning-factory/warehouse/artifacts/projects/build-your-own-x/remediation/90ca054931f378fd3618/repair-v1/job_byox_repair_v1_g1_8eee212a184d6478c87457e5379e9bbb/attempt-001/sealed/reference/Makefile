CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror

BUILD := build
TARGET := $(BUILD)/minic

.PHONY: all clean test

all: $(TARGET)

$(TARGET): src/minic.c | $(BUILD)
	$(CC) $(CFLAGS) $< -o $@

$(BUILD):
	mkdir -p $(BUILD)

test: all
	python3 ../reference_tests/run_tests.py $(TARGET)

clean:
	rm -f $(TARGET)
