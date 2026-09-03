CC ?= cc
PYTHON ?= /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -g
LDFLAGS ?=

.PHONY: all clean check

all: msh

msh: src/msh.o
	$(CC) $(LDFLAGS) -o $@ $^

src/msh.o: src/msh.c include/msh.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

check: msh
	MSH_BIN="$(CURDIR)/msh" PYTHONDONTWRITEBYTECODE=1 "$(PYTHON)" ../../public_tests/test_shell.py

clean:
	rm -f src/msh.o msh
