CC ?= cc
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -Iinclude

.PHONY: all clean check

all: mica

mica: src/mica.c include/mica_limits.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ src/mica.c

check: mica
	cd ../.. && MICA_BIN=sealed/reference/mica python3 sealed/reference_tests/test_reference.py

clean:
	rm -f mica
