CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -Iinclude

BUILD := build
TARGET := $(BUILD)/minic
SOURCES := src/main.c src/source.c src/interpreter.c
OBJECTS := $(SOURCES:src/%.c=$(BUILD)/%.o)

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) $(OBJECTS) -o $@

$(BUILD)/%.o: src/%.c include/minic.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD):
	mkdir -p $(BUILD)

test: all
	python3 ../public_tests/run_tests.py $(TARGET)

clean:
	rm -f $(OBJECTS) $(TARGET)
