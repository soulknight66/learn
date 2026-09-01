# PR review: fold constant expressions before bytecode emission

Review `proposed/optimizer.py` as a production change. Submit comments with severity, an
observable counterexample, and a repair direction. Consider guest-language semantics,
diagnostics/source locations, compile-time resource use, pass placement, and tests. Do not
assume an optimization is valid merely because both operands are syntactically constant.
