# Why this should not ship

Status: **PARTIAL / NOT_PRODUCTION_READY**. The pack has bounded local validation, not a
security or compatibility commitment. Missing work includes recursion/nesting limits in the
parser, memory/output quotas, stable serialized
bytecode with versioning, Unicode policy, richer location-preserving diagnostics, fuzzing at
much larger scale, profiler-guided optimization, package signing, and a hostile-input sandbox.
Python process isolation and `max_steps` do not bound memory or wall time. There is no module
system, lexical scope, functions, debugger, tracing interface, or backward-compatibility plan.
