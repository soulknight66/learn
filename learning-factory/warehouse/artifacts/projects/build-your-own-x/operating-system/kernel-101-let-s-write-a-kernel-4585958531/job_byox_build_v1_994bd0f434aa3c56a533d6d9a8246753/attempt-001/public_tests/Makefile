CC ?= cc
SOURCE_DIR ?= ../starter
BUILD_DIR := build
SOURCE_TAG := $(notdir $(abspath $(SOURCE_DIR)))
TEST_BIN := $(BUILD_DIR)/public_tests_$(SOURCE_TAG)
SOURCES := $(SOURCE_DIR)/src/frames.c $(SOURCE_DIR)/src/scheduler.c \
	$(SOURCE_DIR)/src/vm.c $(SOURCE_DIR)/src/ramfs.c
CFLAGS := -std=c11 -Wall -Wextra -Werror -pedantic -I$(SOURCE_DIR)/include

.PHONY: all test stage1 stage2 stage3 stage4 clean FORCE

all: test

$(TEST_BIN): FORCE test_kernel.c $(SOURCES) $(SOURCE_DIR)/include/tinykernel.h
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) test_kernel.c $(SOURCES) -o $@

test: $(TEST_BIN)
	$(TEST_BIN) all

stage1: $(TEST_BIN)
	$(TEST_BIN) 1

stage2: $(TEST_BIN)
	$(TEST_BIN) 2

stage3: $(TEST_BIN)
	$(TEST_BIN) 3

stage4: $(TEST_BIN)
	$(TEST_BIN) 4

clean:
	rm -rf $(BUILD_DIR)

FORCE:
