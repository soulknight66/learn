CC ?= cc
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror
CPPFLAGS ?= -Iinclude

.PHONY: all clean

all: mica

mica: src/mica.c include/mica_limits.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ src/mica.c

clean:
	rm -f mica
