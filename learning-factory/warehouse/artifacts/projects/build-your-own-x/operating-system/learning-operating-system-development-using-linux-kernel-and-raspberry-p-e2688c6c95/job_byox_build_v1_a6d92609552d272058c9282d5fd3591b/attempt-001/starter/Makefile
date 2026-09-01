CC ?= cc
AR ?= ar
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -Iinclude

BUILD := build
LIB := $(BUILD)/libpebble.a
OBJECT := $(BUILD)/pebble.o
PUBLIC_BIN := $(BUILD)/public_tests

.PHONY: all public clean

all: $(LIB)

public: $(PUBLIC_BIN)
	./$(PUBLIC_BIN)

$(BUILD):
	mkdir -p $(BUILD)

$(OBJECT): src/pebble.c include/pebble.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c src/pebble.c -o $(OBJECT)

$(LIB): $(OBJECT)
	$(AR) rcs $(LIB) $(OBJECT)

$(PUBLIC_BIN): ../public_tests/test_public.c $(LIB)
	$(CC) $(CPPFLAGS) $(CFLAGS) ../public_tests/test_public.c $(LIB) -o $(PUBLIC_BIN)

clean:
	rm -rf $(BUILD)
