# bytehist

`bytehist` reads arbitrary bytes from standard input or one named file and
prints a deterministic histogram. A name of `-` is an ordinary file name, not
an option.

## Build and test

Run these commands from this `submission/` directory:

~~~sh
make
make test
~~~

The default target and `make all` both produce `build/bytehist`. The test target
builds a C module check and runs the Python black-box suite. Test scratch data
is created only below `build/test-tmp`.

Remove generated objects, executables, and test scratch data with:

~~~sh
make clean
~~~

## Usage

Read standard input:

~~~sh
printf 'banana\n' | ./build/bytehist
~~~

Read a named binary file:

~~~sh
./build/bytehist path/to/input.bin
~~~

Supplying more than one argument is a usage error. Input, output, resource, and
count-range failures return status 1; usage errors return status 2.

## Known limitations

Diagnostics intentionally identify the failure class without echoing the path
or operating-system error text. This keeps arbitrary path bytes out of the
diagnostic stream. No known limitation violates the stated unit contract.

## Provenance and validation

All files under this submission were learner-authored from the three supplied
kickoff packet files and locally executed experiments. No optional reference,
external course content, or published solution was consulted.

Validation label: `LEARNER_SELF_TESTED_AWAITING_INDEPENDENT_VALIDATION`. This
label is not an independent completion decision.
