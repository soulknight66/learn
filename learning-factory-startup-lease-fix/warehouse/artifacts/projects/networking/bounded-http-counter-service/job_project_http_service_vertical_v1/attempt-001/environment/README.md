# Reproducible environment

Required: CPython 3.11 or newer on a platform with IPv4 loopback and the standard-library
`selectors`, `socket`, and `threading` modules. No packages and no external network are used.
Commands are argv-based; validation sets bytecode suppression and a deterministic C.UTF-8
locale. Exact OS/interpreter information is captured by the benchmark at execution time.
