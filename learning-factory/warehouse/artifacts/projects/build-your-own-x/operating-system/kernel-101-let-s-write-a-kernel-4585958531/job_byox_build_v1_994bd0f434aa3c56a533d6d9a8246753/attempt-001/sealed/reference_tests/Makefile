CC ?= cc
SOURCE_DIR ?= ../reference
BUILD_DIR := build
TEST_BIN := $(BUILD_DIR)/reference_tests
SANITIZE_BIN := $(BUILD_DIR)/reference_tests_sanitize
SOURCES := $(SOURCE_DIR)/src/frames.c $(SOURCE_DIR)/src/scheduler.c \
	$(SOURCE_DIR)/src/vm.c $(SOURCE_DIR)/src/ramfs.c
CFLAGS := -std=c11 -Wall -Wextra -Werror -pedantic -I$(SOURCE_DIR)/include

.PHONY: all test sanitize clean

all: test

$(TEST_BIN): test_edge_cases.c $(SOURCES) $(SOURCE_DIR)/include/tinykernel.h
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) test_edge_cases.c $(SOURCES) -o $@

$(SANITIZE_BIN): test_edge_cases.c $(SOURCES) $(SOURCE_DIR)/include/tinykernel.h
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -O1 -g -fno-omit-frame-pointer \
		-fsanitize=address,undefined test_edge_cases.c $(SOURCES) -o $@

test: $(TEST_BIN)
	$(TEST_BIN)

sanitize: $(SANITIZE_BIN)
	ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 $(SANITIZE_BIN)

clean:
	rm -rf $(BUILD_DIR)
