CC ?= cc
AR ?= ar
CPPFLAGS ?= -Iinclude -D_POSIX_C_SOURCE=200809L
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -g
DEPFLAGS ?= -MMD -MP
LDFLAGS ?=
LDLIBS ?=

TARGET := minish
LIBRARY := libminish.a
BUILD_DIR := build
LIB_SOURCES := src/shell.c src/lexer.c src/parser.c src/executor.c
LIB_OBJECTS := $(LIB_SOURCES:src/%.c=$(BUILD_DIR)/%.o)
MAIN_OBJECT := $(BUILD_DIR)/main.o

.PHONY: all clean

all: $(TARGET) $(LIBRARY)

$(TARGET): $(MAIN_OBJECT) $(LIBRARY)
	$(CC) $(LDFLAGS) -o $@ $(MAIN_OBJECT) $(LIBRARY) $(LDLIBS)

$(LIBRARY): $(LIB_OBJECTS)
	$(AR) rcs $@ $^

$(BUILD_DIR)/%.o: src/%.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(DEPFLAGS) -c $< -o $@

$(BUILD_DIR):
	mkdir -p $@

clean:
	rm -rf -- $(BUILD_DIR) $(TARGET) $(LIBRARY)

-include $(LIB_OBJECTS:.o=.d) $(MAIN_OBJECT:.o=.d)
