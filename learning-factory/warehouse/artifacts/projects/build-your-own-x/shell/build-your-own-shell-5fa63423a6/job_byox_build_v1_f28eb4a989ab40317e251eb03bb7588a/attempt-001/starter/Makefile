CC ?= cc
CPPFLAGS ?= -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -g
LDFLAGS ?=

SOURCES := src/main.c src/parser.c src/execute.c
OBJECTS := $(SOURCES:.c=.o)

.PHONY: all clean check check-milestones

all: byosh

byosh: $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $(OBJECTS)

src/%.o: src/%.c include/byosh.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

check: byosh
	$(MAKE) -C ../public_tests baseline

check-milestones: byosh
	$(MAKE) -C ../public_tests milestones SHELL_UNDER_TEST=../starter/byosh

clean:
	rm -f byosh $(OBJECTS)
