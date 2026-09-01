CC ?= cc
AR ?= ar
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -Iinclude

BUILD := build
LIB := $(BUILD)/libpebble.a
OBJECT := $(BUILD)/pebble.o

.PHONY: all clean

all: $(LIB)

$(BUILD):
	mkdir -p $(BUILD)

$(OBJECT): src/pebble.c include/pebble.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c src/pebble.c -o $(OBJECT)

$(LIB): $(OBJECT)
	$(AR) rcs $(LIB) $(OBJECT)

clean:
	rm -rf $(BUILD)
