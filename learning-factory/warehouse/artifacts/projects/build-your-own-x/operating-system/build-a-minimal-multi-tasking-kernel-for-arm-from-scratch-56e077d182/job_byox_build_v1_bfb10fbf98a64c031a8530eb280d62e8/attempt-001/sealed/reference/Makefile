CC ?= cc
AR ?= ar
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic
CPPFLAGS ?= -I../../starter/include

.PHONY: all clean

all: libtinyarm-reference.a

libtinyarm-reference.a: build/kernel.o
	$(AR) rcs $@ $^

build/kernel.o: src/kernel.c ../../starter/include/tinyarm.h
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

clean:
	rm -f libtinyarm-reference.a
	rm -rf build
