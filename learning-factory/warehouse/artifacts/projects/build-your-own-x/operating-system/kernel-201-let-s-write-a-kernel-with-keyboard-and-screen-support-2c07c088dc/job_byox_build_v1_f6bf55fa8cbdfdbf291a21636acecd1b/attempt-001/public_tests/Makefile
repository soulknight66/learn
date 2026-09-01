CC := gcc
PROJECT ?= ../starter
BUILD := .build/$(notdir $(abspath $(PROJECT)))
CFLAGS := -std=c11 -Wall -Wextra -Werror -pedantic -O2
CPPFLAGS := -I$(PROJECT)/include -I.
SOURCES := test_main.c test_terminal_public.c test_keyboard_public.c \
	$(PROJECT)/src/terminal.c $(PROJECT)/src/keyboard.c

.PHONY: all run clean

all: $(BUILD)/public_tests

$(BUILD)/public_tests: $(SOURCES)
	@mkdir -p $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SOURCES) -o $@

run: $(BUILD)/public_tests
	./$(BUILD)/public_tests

clean:
	rm -rf .build
