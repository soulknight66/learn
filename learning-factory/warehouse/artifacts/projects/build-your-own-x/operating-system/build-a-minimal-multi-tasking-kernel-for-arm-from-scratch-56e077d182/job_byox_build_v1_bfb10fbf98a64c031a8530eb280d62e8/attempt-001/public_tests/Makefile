CC ?= cc
IMPL_DIR ?= ../starter
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic
CPPFLAGS ?= -I$(IMPL_DIR)/include
SANITIZE ?= 0

ifeq ($(SANITIZE),1)
CFLAGS += -O1 -fno-omit-frame-pointer -fsanitize=address,undefined
LDFLAGS += -fsanitize=address,undefined
endif

.PHONY: all test clean

all: public_tests

public_tests: test_public.c $(IMPL_DIR)/src/kernel.c $(IMPL_DIR)/include/tinyarm.h
	$(CC) $(CPPFLAGS) $(CFLAGS) test_public.c $(IMPL_DIR)/src/kernel.c $(LDFLAGS) -o $@

test: public_tests
	./public_tests

clean:
	rm -f public_tests
