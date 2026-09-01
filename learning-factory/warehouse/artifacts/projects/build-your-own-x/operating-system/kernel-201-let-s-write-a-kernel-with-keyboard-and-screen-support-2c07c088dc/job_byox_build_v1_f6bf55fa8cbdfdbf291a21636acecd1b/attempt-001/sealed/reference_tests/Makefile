CC := gcc
REFERENCE := ../reference
BUILD := .build
CPPFLAGS := -I$(REFERENCE)/include -I.
BASE_CFLAGS := -std=c11 -Wall -Wextra -Werror -pedantic -O2
TEST_SOURCES := test_main.c test_terminal.c test_keyboard.c \
	$(REFERENCE)/src/terminal.c $(REFERENCE)/src/keyboard.c

.PHONY: all run sanitize clean

all: $(BUILD)/reference_tests

$(BUILD)/reference_tests: $(TEST_SOURCES)
	@mkdir -p $(BUILD)
	$(CC) $(CPPFLAGS) $(BASE_CFLAGS) $(TEST_SOURCES) -o $@

run: $(BUILD)/reference_tests
	./$(BUILD)/reference_tests

$(BUILD)/reference_tests_sanitize: $(TEST_SOURCES)
	@mkdir -p $(BUILD)
	$(CC) $(CPPFLAGS) $(BASE_CFLAGS) -O1 -g \
		-fsanitize=address,undefined -fno-omit-frame-pointer $(TEST_SOURCES) -o $@

sanitize: $(BUILD)/reference_tests_sanitize
	ASAN_OPTIONS=detect_leaks=0 ./$(BUILD)/reference_tests_sanitize

clean:
	rm -rf $(BUILD)
