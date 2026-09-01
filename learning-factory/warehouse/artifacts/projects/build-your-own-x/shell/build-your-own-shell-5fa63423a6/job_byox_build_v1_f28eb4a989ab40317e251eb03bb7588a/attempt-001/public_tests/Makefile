CC ?= cc
CPPFLAGS ?= -I../starter/include
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -g
SHELL_UNDER_TEST ?= ../starter/byosh

.PHONY: all baseline milestones cli clean

all: baseline

baseline: test_baseline
	./test_baseline

milestones: test_parser_milestones
	./test_parser_milestones

cli:
	python3 ./test_cli.py $(SHELL_UNDER_TEST)

test_baseline: test_baseline.c ../starter/src/parser.c ../starter/include/byosh.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ test_baseline.c ../starter/src/parser.c

test_parser_milestones: test_parser_milestones.c ../starter/src/parser.c ../starter/include/byosh.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ test_parser_milestones.c ../starter/src/parser.c

clean:
	rm -f test_baseline test_parser_milestones
