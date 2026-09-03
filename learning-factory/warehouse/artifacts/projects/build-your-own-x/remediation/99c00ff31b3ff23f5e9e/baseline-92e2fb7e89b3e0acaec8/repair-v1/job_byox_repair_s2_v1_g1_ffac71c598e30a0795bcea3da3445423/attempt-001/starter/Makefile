CC ?= cc
CFLAGS ?= -std=c11 -O2 -g
CPPFLAGS ?= -Iinclude
WARNINGS = -Wall -Wextra -Wpedantic -Werror

SOURCES = src/main.c src/lexer.c src/pipeline.c
OBJECTS = $(SOURCES:.c=.o)

.PHONY: all clean test

all: pebble

pebble: $(OBJECTS)
	$(CC) $(CFLAGS) $(WARNINGS) $(OBJECTS) -o $@

src/%.o: src/%.c include/pebble.h
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARNINGS) -c $< -o $@

src/lexer.o: include/lexer.h

test: pebble
	python3 ../public_tests/run_tests.py

clean:
	rm -f $(OBJECTS) pebble
