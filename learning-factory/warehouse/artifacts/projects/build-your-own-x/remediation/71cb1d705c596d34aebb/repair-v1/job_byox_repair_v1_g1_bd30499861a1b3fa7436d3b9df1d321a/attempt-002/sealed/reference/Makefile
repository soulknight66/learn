CC ?= cc
CFLAGS ?= -O2 -g
CPPFLAGS ?=
WARNFLAGS = -Wall -Wextra -Wpedantic -Werror
POSIXFLAGS = -D_POSIX_C_SOURCE=200809L

.PHONY: all clean test

all: minish

minish: minish.c
	$(CC) $(CPPFLAGS) $(POSIXFLAGS) $(CFLAGS) $(WARNFLAGS) -std=c11 -o $@ $<

test: minish
	python3 ../reference_tests/test_reference.py

clean:
	rm -f minish
