CC := gcc
REFERENCE := ../reference
BUILD := .build
CPPFLAGS := -I$(REFERENCE)/include
BASE_CFLAGS := -std=c11 -Wall -Wextra -Werror -pedantic -O2
SOURCES := test_stress.c $(REFERENCE)/src/terminal.c $(REFERENCE)/src/keyboard.c

.PHONY: all run sanitize clean

all: $(BUILD)/test_stress

$(BUILD)/test_stress: $(SOURCES)
	@mkdir -p $(BUILD)
	$(CC) $(CPPFLAGS) $(BASE_CFLAGS) $(SOURCES) -o $@

run: $(BUILD)/test_stress
	./$(BUILD)/test_stress

$(BUILD)/test_stress_sanitize: $(SOURCES)
	@mkdir -p $(BUILD)
	$(CC) $(CPPFLAGS) $(BASE_CFLAGS) -O1 -g \
		-fsanitize=address,undefined -fno-omit-frame-pointer $(SOURCES) -o $@

sanitize: $(BUILD)/test_stress_sanitize
	ASAN_OPTIONS=detect_leaks=0 ./$(BUILD)/test_stress_sanitize

clean:
	rm -rf $(BUILD)
