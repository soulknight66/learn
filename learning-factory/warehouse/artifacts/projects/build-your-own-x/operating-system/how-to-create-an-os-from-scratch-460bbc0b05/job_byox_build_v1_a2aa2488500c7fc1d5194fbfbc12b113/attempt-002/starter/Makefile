CC ?= cc
AR ?= ar

CPPFLAGS ?= -Iinclude
WARN_FLAGS := -std=c11 -Wall -Wextra -Werror -pedantic
CORE_CFLAGS ?= $(WARN_FLAGS) -ffreestanding
TEST_CFLAGS ?= $(WARN_FLAGS)

BUILD_DIR := build
SOURCES := src/scheduler.c src/vm.c src/ramfs.c
OBJECTS := $(SOURCES:src/%.c=$(BUILD_DIR)/%.o)
LIBRARY := $(BUILD_DIR)/libmicaos.a
TEST_BINARY := $(BUILD_DIR)/test_public

.PHONY: all build test clean

all: build

build: $(LIBRARY)

$(BUILD_DIR)/%.o: src/%.c include/micaos.h
	mkdir -p $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CORE_CFLAGS) -c $< -o $@

$(LIBRARY): $(OBJECTS)
	$(AR) rcs $@ $(OBJECTS)

$(TEST_BINARY): ../public_tests/test_public.c $(LIBRARY)
	$(CC) $(CPPFLAGS) $(TEST_CFLAGS) $< $(LIBRARY) -o $@

test: $(TEST_BINARY)
	./$(TEST_BINARY)

clean:
	rm -rf $(BUILD_DIR)
