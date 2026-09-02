CC ?= cc
PYTHON ?= python3
REFERENCE ?= ../sealed/reference
BUILD_DIR := build
TARGET := $(BUILD_DIR)/vector_runner

CPPFLAGS := -I$(REFERENCE)/include
CFLAGS := -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic
SANITIZERS ?= -fsanitize=address,undefined -fno-omit-frame-pointer
SOURCES := vector_runner.c $(REFERENCE)/kernel/scheduler.c \
	$(REFERENCE)/kernel/vm.c $(REFERENCE)/kernel/ramfs.c

.PHONY: all test clean

all: $(TARGET)

$(TARGET): $(SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANITIZERS) $(SOURCES) -o $@

test: $(TARGET)
	$(PYTHON) -m unittest test_run_vectors.py -v
	$(PYTHON) run_vectors.py --vectors cases/boundaries.json --runner ./$(TARGET)

clean:
	rm -rf $(BUILD_DIR)
