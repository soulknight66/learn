CC ?= cc
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -g
LDFLAGS ?=

SOURCES := src/main.c src/shell.c
OBJECTS := $(SOURCES:.c=.o)

.PHONY: all clean check

all: msh

msh: $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $(OBJECTS)

src/%.o: src/%.c include/msh.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

check: msh
	MSH_BIN="$(CURDIR)/msh" python3 ../public_tests/test_shell.py

clean:
	rm -f $(OBJECTS) msh
