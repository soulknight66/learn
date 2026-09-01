CC ?= cc
STARTER_DIR ?= ../starter
STARTER_TEST_LIBRARY ?= $(STARTER_DIR)/libbyosh_test.a
CPPFLAGS ?= -I$(STARTER_DIR)/include
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -g
SHELL_UNDER_TEST ?= ../starter/byosh

.PHONY: all baseline milestones cli clean starter-test-library

all: baseline

baseline: test_baseline
	./test_baseline

milestones: test_parser_milestones
	./test_parser_milestones

cli:
	python3 ./test_cli.py $(SHELL_UNDER_TEST)

starter-test-library:
	$(MAKE) -C $(STARTER_DIR) libbyosh_test.a

test_baseline: test_baseline.c $(STARTER_DIR)/include/byosh.h starter-test-library
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ test_baseline.c $(STARTER_TEST_LIBRARY)

test_parser_milestones: test_parser_milestones.c $(STARTER_DIR)/include/byosh.h starter-test-library
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ test_parser_milestones.c $(STARTER_TEST_LIBRARY)

clean:
	$(RM) test_baseline test_parser_milestones
