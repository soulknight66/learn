CC ?= cc
CPPFLAGS ?= -D_POSIX_C_SOURCE=200809L -I../reference/include
CFLAGS ?= -std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror
LDFLAGS ?=

.PHONY: all clean test

all: parser_tests jobs_tests pg_probe

parser_tests: test_parser.c ../reference/src/parser.c ../reference/include/msh.h
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ test_parser.c ../reference/src/parser.c

jobs_tests: test_jobs.c ../reference/src/jobs.c ../reference/include/msh.h
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ test_jobs.c ../reference/src/jobs.c

pg_probe: pg_probe.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ pg_probe.c

test: all
	./parser_tests
	./jobs_tests
	python3 integration_test.py --shell ../reference/msh-reference --pg-probe ./pg_probe
	python3 adversarial_test.py --shell ../reference/msh-reference
	python3 interactive_test.py --shell ../reference/msh-reference

clean:
	rm -f parser_tests jobs_tests pg_probe
