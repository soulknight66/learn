# Code-review exercises

## R1: arithmetic shortcut

Review a VM that implements division as `stack << left / right` and modulo as `stack << left % right`. List semantic, type, zero-divisor, and range checks needed before those lines could implement Pebble.

## R2: eager declaration

Review a compiler that inserts a new name into the current scope before compiling its initializer. Give one program with no outer binding and one with an outer binding that reveal the behavior change.

## R3: shallow verifier

Review a VM that validates only the opcode symbol as each instruction executes. Identify failures that should be detected before any program output occurs, including failures on unreachable instructions.

## R4: service wrapper

Review a proposed network service that calls `Pebble.run(request_body)` with the default step budget. Identify resources not controlled by that budget and propose enforcement layers.
