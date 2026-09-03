CC ?= cc
CFLAGS ?= -std=c17 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -O2 -g
CPPFLAGS ?= -Iinclude

SOURCES = src/main.c src/lexer.c src/parser.c src/execute.c
OBJECTS = $(SOURCES:.c=.o)

.PHONY: all clean

all: minish

minish: $(OBJECTS)
	$(CC) $(CFLAGS) $(OBJECTS) -o $@

src/%.o: src/%.c include/minish.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(OBJECTS) minish
