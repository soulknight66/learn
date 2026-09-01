# Environment

Required: Python 3 standard library and a C11-capable `gcc`. The build harness uses
`-Wall -Wextra -Werror -pedantic -O2 -fno-omit-frame-pointer` and records the exact compiler,
platform, and flags during validation. Address/undefined sanitizers are compiled and executed
on a harmless probe; sanitized model testing runs only if both steps succeed. No sanitizer is
assumed and no network is used.
