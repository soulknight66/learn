CC ?= cc
SOURCE_DIR ?= ../starter
BUILD_DIR := build
SOURCES := $(SOURCE_DIR)/src/frames.c $(SOURCE_DIR)/src/scheduler.c \
	$(SOURCE_DIR)/src/vm.c $(SOURCE_DIR)/src/ramfs.c
CFLAGS := -O2 -std=c11 -Wall -Wextra -Werror -pedantic -I$(SOURCE_DIR)/include

.PHONY: all build clean

all: build

build: $(BUILD_DIR)/bench_core

$(BUILD_DIR)/bench_core: bench_core.c $(SOURCES) $(SOURCE_DIR)/include/tinykernel.h
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) bench_core.c $(SOURCES) -o $@

clean:
	rm -rf $(BUILD_DIR)
