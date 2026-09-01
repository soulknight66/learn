CC ?= cc
BUILD_DIR := build
REFERENCE := ../reference
REFERENCE_SOURCES := $(REFERENCE)/src/frames.c $(REFERENCE)/src/scheduler.c \
	$(REFERENCE)/src/vm.c $(REFERENCE)/src/ramfs.c
CFLAGS := -std=c11 -Wall -Wextra -Werror -pedantic -Iinclude -I$(REFERENCE)/include

.PHONY: all test clean

all: test

$(BUILD_DIR)/test_audits: test_audits.c src/invariant_checks.c \
	include/invariant_checks.h $(REFERENCE_SOURCES)
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) test_audits.c src/invariant_checks.c $(REFERENCE_SOURCES) -o $@

test: $(BUILD_DIR)/test_audits
	$(BUILD_DIR)/test_audits

clean:
	rm -rf $(BUILD_DIR)
