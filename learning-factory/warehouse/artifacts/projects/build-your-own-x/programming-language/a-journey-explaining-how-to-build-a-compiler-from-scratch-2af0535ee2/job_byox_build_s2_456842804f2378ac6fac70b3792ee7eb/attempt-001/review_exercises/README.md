# Code-review exercise: declaration timing

Review `candidate_parser.c`, which sketches a proposed `let` parser. Assume omitted helpers have the same contracts as the starter header and grammar.

Find at least four correctness or robustness issues. Pay particular attention to when a name becomes visible, bounded copying, error propagation, and whether a failed initializer leaves compiler state usable.

The answer and a safer sequence are confined to this exercise’s `sealed/` directory.
