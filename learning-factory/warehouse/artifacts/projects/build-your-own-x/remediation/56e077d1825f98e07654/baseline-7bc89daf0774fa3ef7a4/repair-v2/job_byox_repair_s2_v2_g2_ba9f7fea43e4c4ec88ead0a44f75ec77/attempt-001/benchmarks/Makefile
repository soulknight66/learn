CC ?= cc
REFERENCE ?= ../sealed/reference
TARGET := build/bench_host

CPPFLAGS := -I$(REFERENCE)/include
CFLAGS := -std=c11 -O2 -Wall -Wextra -Werror -pedantic
SOURCES := bench_host.c $(REFERENCE)/kernel/scheduler.c

.PHONY: all run clean

all: $(TARGET)

$(TARGET): $(SOURCES)
	@mkdir -p $(@D)
	$(CC) $(CPPFLAGS) $(CFLAGS) $(SOURCES) -o $@

run: $(TARGET)
	./$(TARGET)

clean:
	rm -rf build
