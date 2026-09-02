# Starter

`pebble/` defines the required module layout, public names, and CLI boundary. Intentional TODOs raise
`NotImplementedError`; replacing them is the exercise. Do not rename public functions or change the
exception inheritance tree because tests import them directly.

Suggested implementation order is `reader.py`, `env.py`, `values.py`, `interpreter.py`, then `cli.py`.
Keep helpers private unless a new public contract is documented.
