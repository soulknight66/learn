CC ?= cc
AR ?= ar
ARFLAGS = rcs
CPPFLAGS ?= -Iinclude
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -Werror -g
LDFLAGS ?=

MAIN_SOURCE := src/main.c
SOURCES := $(MAIN_SOURCE) src/parser.c src/pipeline.c src/execute.c
OBJECTS := $(SOURCES:.c=.o)
TEST_OBJECTS := $(filter-out $(MAIN_SOURCE:.c=.o),$(OBJECTS))
TEST_LIBRARY := libbyosh_test.a

.PHONY: all clean check check-milestones

all: byosh

byosh: $(OBJECTS)
	$(CC) $(LDFLAGS) -o $@ $(OBJECTS)

$(TEST_LIBRARY): $(TEST_OBJECTS)
	$(RM) $@
	$(AR) $(ARFLAGS) $@ $^

src/%.o: src/%.c include/byosh.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c -o $@ $<

check: byosh
	$(MAKE) -C ../public_tests baseline

check-milestones: byosh
	$(MAKE) -C ../public_tests milestones SHELL_UNDER_TEST=../starter/byosh

clean:
	$(RM) byosh $(OBJECTS) $(TEST_LIBRARY)
