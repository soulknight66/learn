PYTHON ?= /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
OUTPUT ?= build/cinder

.PHONY: all test clean

all:
	$(PYTHON) ../environment/build.py forth.S -o $(OUTPUT)

test: all
	CINDER_BIN=$(abspath $(OUTPUT)) $(PYTHON) -m unittest discover -s ../public_tests -v

clean:
	rm -f $(OUTPUT)
