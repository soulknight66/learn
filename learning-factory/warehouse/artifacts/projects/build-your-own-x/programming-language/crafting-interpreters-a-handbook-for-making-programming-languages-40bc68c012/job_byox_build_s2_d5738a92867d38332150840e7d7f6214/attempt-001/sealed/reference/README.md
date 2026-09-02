# Sealed reference implementation

This directory contains the complete Java reference for the Mica contract. It is validator/instructor
material, not learner-visible material. The implementation has two independent back ends sharing only
tokens, AST, value rules, and the parser front end.

Run the public suite with `SOURCE_ROOT=sealed/reference public_tests/run.sh`; run the larger sealed suite
with `sealed/reference_tests/run.sh`.
