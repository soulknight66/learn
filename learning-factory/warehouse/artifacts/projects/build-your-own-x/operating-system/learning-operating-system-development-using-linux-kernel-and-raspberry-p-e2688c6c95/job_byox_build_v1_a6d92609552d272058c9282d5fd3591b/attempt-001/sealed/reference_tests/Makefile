CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -I../reference/include

BUILD := build
TEST_BIN := $(BUILD)/reference_tests
PUBLIC_BIN := $(BUILD)/public_against_reference
SANITIZE_BIN := $(BUILD)/reference_tests_sanitize
REFERENCE_SOURCE := ../reference/src/pebble.c

.PHONY: all test public sanitize clean

all: $(TEST_BIN)

test: $(TEST_BIN)
	./$(TEST_BIN)

public: $(PUBLIC_BIN)
	./$(PUBLIC_BIN)

sanitize: $(SANITIZE_BIN)
	ASAN_OPTIONS=detect_leaks=1 ./$(SANITIZE_BIN)

$(BUILD):
	mkdir -p $(BUILD)

$(TEST_BIN): test_reference.c $(REFERENCE_SOURCE) ../reference/include/pebble.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) test_reference.c $(REFERENCE_SOURCE) -o $(TEST_BIN)

$(PUBLIC_BIN): ../../public_tests/test_public.c $(REFERENCE_SOURCE) ../reference/include/pebble.h | $(BUILD)
	$(CC) $(CPPFLAGS) $(CFLAGS) ../../public_tests/test_public.c $(REFERENCE_SOURCE) -o $(PUBLIC_BIN)

$(SANITIZE_BIN): test_reference.c $(REFERENCE_SOURCE) ../reference/include/pebble.h | $(BUILD)
	$(CC) $(CPPFLAGS) -std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror \
		-fsanitize=address,undefined -fno-omit-frame-pointer \
		test_reference.c $(REFERENCE_SOURCE) -o $(SANITIZE_BIN)

clean:
	rm -rf $(BUILD)
