FPC ?= fpc
FPCFLAGS ?= -Mobjfpc -Sh -O1 -g -gl

.PHONY: all clean

all: bin/mica

bin/mica: src/mica.pas src/mica_types.pas src/lexer.pas src/compiler.pas src/vm.pas
	mkdir -p bin units
	$(FPC) $(FPCFLAGS) -Fusrc -FUunits -FEbin src/mica.pas

clean:
	rm -f bin/mica units/*.o units/*.ppu
