CC ?= cc
AR ?= ar
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic
CPPFLAGS ?= -Iinclude

.PHONY: all clean

all: libtinyarm.a

libtinyarm.a: build/kernel.o
	$(AR) rcs $@ $^

build/kernel.o: src/kernel.c include/tinyarm.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

clean:
	rm -f libtinyarm.a
	rm -rf build
