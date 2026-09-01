CC ?= cc
AR ?= ar
ARFLAGS = rcs

CPPFLAGS ?= -Iinclude
WARNINGS := -Wall -Wextra -Werror -pedantic
CORE_CFLAGS ?= -std=c11 $(WARNINGS) -ffreestanding
TEST_CFLAGS ?= -std=c11 $(WARNINGS)

BUILD_DIR := build
SOURCES := scheduler.c vm.c ramfs.c
OBJECTS := $(SOURCES:%.c=$(BUILD_DIR)/%.o)
LIBRARY := $(BUILD_DIR)/libmicaos.a
TEST_SOURCE := ../reference_tests/test_reference.c
TEST_BINARY := $(BUILD_DIR)/test_reference
STARTER_HEADER := ../../starter/include/micaos.h

.PHONY: all clean interface-check test

all: $(LIBRARY)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.o: %.c include/micaos.h | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CORE_CFLAGS) -c $< -o $@

$(LIBRARY): $(OBJECTS)
	$(AR) $(ARFLAGS) $@ $^

interface-check:
	cmp include/micaos.h $(STARTER_HEADER)

$(TEST_BINARY): $(TEST_SOURCE) $(LIBRARY) include/micaos.h
	$(CC) $(CPPFLAGS) $(TEST_CFLAGS) $(TEST_SOURCE) $(LIBRARY) -o $@

test: interface-check $(TEST_BINARY)
	./$(TEST_BINARY)

clean:
	rm -rf -- $(BUILD_DIR)
