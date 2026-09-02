CC ?= cc
REFERENCE ?= ../reference
BUILD_DIR := build
TARGET := $(BUILD_DIR)/test_reference

CPPFLAGS := -I$(REFERENCE)/include
CFLAGS := -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic
SANITIZERS ?= -fsanitize=address,undefined -fno-omit-frame-pointer
SOURCES := test_reference.c $(REFERENCE)/kernel/scheduler.c \
	$(REFERENCE)/kernel/vm.c $(REFERENCE)/kernel/ramfs.c

.PHONY: all test clean

all: $(TARGET)

$(TARGET): $(SOURCES)
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SANITIZERS) $(SOURCES) -o $@

test: $(TARGET)
	./$(TARGET)

clean:
	rm -rf $(BUILD_DIR)
