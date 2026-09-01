CC ?= cc
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic
CPPFLAGS ?= -I../../starter/include
SANITIZE ?= 0

ifeq ($(SANITIZE),1)
CFLAGS += -O1 -fno-omit-frame-pointer -fsanitize=address,undefined
LDFLAGS += -fsanitize=address,undefined
endif

.PHONY: all test clean

all: reference_tests

reference_tests: test_reference.c ../reference/src/kernel.c ../../starter/include/tinyarm.h
	$(CC) $(CPPFLAGS) $(CFLAGS) test_reference.c ../reference/src/kernel.c $(LDFLAGS) -o $@

test: reference_tests
	./reference_tests

clean:
	rm -f reference_tests
