CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
CPPFLAGS ?= -Iinclude

BUILD_DIR := build
TARGET := $(BUILD_DIR)/sprig
SOURCES := src/main.c src/lexer.c src/compiler.c src/vm.c
OBJECTS := $(SOURCES:src/%.c=$(BUILD_DIR)/%.o)

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) $(OBJECTS) -o $@

$(BUILD_DIR)/%.o: src/%.c include/sprig.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

test: all
	python3 ../reference_tests/run_tests.py --binary $(TARGET)

clean:
	rm -f $(OBJECTS) $(TARGET)
