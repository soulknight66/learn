# Sealed reference implementation

This directory contains an independently written, standard-library-only implementation of the public
Minnow contract. It is evaluator evidence, not learner guidance. The pipeline is split into lexer,
parser, resolver/emitter, binary verifier, and VM modules so failures can be attributed to a stage.

Run its test suite only in the sealed validation context:

```bash
PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
```
