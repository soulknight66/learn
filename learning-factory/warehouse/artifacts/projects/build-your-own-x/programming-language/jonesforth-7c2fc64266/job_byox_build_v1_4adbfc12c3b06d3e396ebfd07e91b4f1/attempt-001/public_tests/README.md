# Public behavioral tests

The unittest suite builds starter/ by default and invokes only the resulting stackvm executable.
It covers representative literals, operators, stack words, comparison, compile atomicity, and
several failures. It intentionally does not reveal every boundary case.

Run it from the repository root:

    python3 -m unittest discover -s public_tests -v

For a separate implementation directory that has the same Makefile and executable contract, set
STACKVM_TARGET to that directory. This hook is for harness use; learner submissions should normally
leave it unset.

