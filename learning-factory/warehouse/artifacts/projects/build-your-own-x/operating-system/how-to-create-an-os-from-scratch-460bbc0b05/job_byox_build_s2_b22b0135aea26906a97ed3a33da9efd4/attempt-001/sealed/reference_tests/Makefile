CC := /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
REFERENCE := ../reference/src/cairn.c
INCLUDE := ../reference/include
CFLAGS := -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
SANITIZER_FLAGS := -std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror \
	-fsanitize=address,undefined -fno-omit-frame-pointer
SANITIZER_LIB := /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64
BUILD := build

.PHONY: all run sanitized benchmark clean

all: $(BUILD)/test_reference $(BUILD)/test_adversarial

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/test_reference: test_reference.c $(REFERENCE) $(INCLUDE)/cairn.h | $(BUILD)
	$(CC) $(CFLAGS) -I$(INCLUDE) test_reference.c $(REFERENCE) -o $@

$(BUILD)/test_adversarial: test_adversarial.c $(REFERENCE) $(INCLUDE)/cairn.h | $(BUILD)
	$(CC) $(CFLAGS) -I$(INCLUDE) test_adversarial.c $(REFERENCE) -o $@

$(BUILD)/test_reference_san: test_reference.c $(REFERENCE) $(INCLUDE)/cairn.h | $(BUILD)
	$(CC) $(SANITIZER_FLAGS) -I$(INCLUDE) test_reference.c $(REFERENCE) -o $@

$(BUILD)/test_adversarial_san: test_adversarial.c $(REFERENCE) $(INCLUDE)/cairn.h | $(BUILD)
	$(CC) $(SANITIZER_FLAGS) -I$(INCLUDE) test_adversarial.c $(REFERENCE) -o $@

$(BUILD)/benchmark: benchmark.c $(REFERENCE) $(INCLUDE)/cairn.h | $(BUILD)
	$(CC) $(CFLAGS) -I$(INCLUDE) benchmark.c $(REFERENCE) -o $@

run: all
	./$(BUILD)/test_reference
	./$(BUILD)/test_adversarial

sanitized: $(BUILD)/test_reference_san $(BUILD)/test_adversarial_san
	ASAN_OPTIONS=detect_leaks=0 LD_LIBRARY_PATH=$(SANITIZER_LIB) \
		./$(BUILD)/test_reference_san
	ASAN_OPTIONS=detect_leaks=0 LD_LIBRARY_PATH=$(SANITIZER_LIB) \
		./$(BUILD)/test_adversarial_san

benchmark: $(BUILD)/benchmark
	./$(BUILD)/benchmark

clean:
	rm -rf $(BUILD)
