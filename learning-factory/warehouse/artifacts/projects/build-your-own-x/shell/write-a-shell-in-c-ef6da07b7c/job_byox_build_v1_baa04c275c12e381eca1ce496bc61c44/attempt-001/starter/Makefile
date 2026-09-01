CC ?= cc
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L -Iinclude
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror
LDFLAGS ?=

TARGET := msh
SOURCES := src/shell.c src/parser.c src/jobs.c
OBJECTS := $(SOURCES:.c=.o)

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $(OBJECTS)

src/%.o: src/%.c include/msh.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

test: all
	python3 ../public_tests/test_shell.py --shell ./msh

clean:
	rm -f $(TARGET) $(OBJECTS)
