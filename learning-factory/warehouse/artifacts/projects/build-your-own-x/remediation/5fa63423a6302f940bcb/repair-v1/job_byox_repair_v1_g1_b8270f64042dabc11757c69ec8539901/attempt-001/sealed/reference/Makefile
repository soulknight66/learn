CC ?= cc
CPPFLAGS += -D_POSIX_C_SOURCE=200809L
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -g
LDFLAGS ?=

TARGET := byosh
SOURCES := main.c lexer.c parser.c jobs.c builtins.c
OBJECTS := $(SOURCES:.c=.o)

.PHONY: all clean test

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $(OBJECTS)

%.o: %.c shell.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

test: $(TARGET)
	$(MAKE) -C ../reference_tests test SHELL_UNDER_TEST=$(abspath $(TARGET))

clean:
	rm -f $(TARGET) $(OBJECTS)
