CC := /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
IMPL ?= ../starter/src/cairn.c
INCLUDE ?= ../starter/include
CFLAGS := -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
BUILD := build

.PHONY: all run clean

all: $(BUILD)/test_public

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/test_public: test_public.c $(IMPL) $(INCLUDE)/cairn.h | $(BUILD)
	$(CC) $(CFLAGS) -I$(INCLUDE) test_public.c $(IMPL) -o $@

run: all
	./$(BUILD)/test_public

clean:
	rm -rf $(BUILD)
