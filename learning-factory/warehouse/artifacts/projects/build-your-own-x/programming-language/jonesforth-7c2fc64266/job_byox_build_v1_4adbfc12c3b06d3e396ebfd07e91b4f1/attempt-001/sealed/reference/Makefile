AS ?= as
LD ?= ld
ASFLAGS ?= --64
LDFLAGS ?=

.PHONY: all clean

all: stackvm

stackvm: stackvm.o
	$(LD) $(LDFLAGS) -o $@ $<

stackvm.o: stackvm.S
	$(AS) $(ASFLAGS) -o $@ $<

clean:
	rm -f stackvm stackvm.o

