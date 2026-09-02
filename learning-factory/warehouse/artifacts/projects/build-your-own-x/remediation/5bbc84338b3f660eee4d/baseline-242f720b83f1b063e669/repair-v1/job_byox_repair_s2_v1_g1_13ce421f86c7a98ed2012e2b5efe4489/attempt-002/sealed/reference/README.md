# Sealed reference implementation

This directory contains an independently generated Python 3.11 implementation of the Pebble contract.
It is validator/instructor material, not learner-visible guidance. It uses no third-party dependencies and
does not execute source through Python evaluation facilities.

Validation should set `PYTHONPATH=sealed/reference`. The implementation includes the required tree walker
and a deliberately smaller optional bytecode compiler/VM that rejects closure-related forms.
