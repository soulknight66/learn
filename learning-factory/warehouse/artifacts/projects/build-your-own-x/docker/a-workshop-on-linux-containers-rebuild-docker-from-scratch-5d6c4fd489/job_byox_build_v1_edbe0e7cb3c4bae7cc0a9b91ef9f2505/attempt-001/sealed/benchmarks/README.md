# Benchmark status and instructor notes

No Minibox benchmark was executed. There are no timing, throughput, memory, or comparison numbers to
report, and the artifact must not be labeled `BENCHMARKED` on the strength of this document.

The useful decomposition is validation, command resolution by rootfs depth and `PATH` candidate
count, state serialization/replacement, fake-backend orchestration, and real namespace/helper launch.
Cold and warm filesystem-cache results should be separate. Failure paths need measurement because
timeout cleanup and state preservation can cost more than successful setup.

Before accepting results, require the exact commit, command, raw samples, environment metadata,
sample count, distribution and uncertainty, rootfs fixture hash, output byte count, and correctness
checks. A real-backend sample is invalid if namespace assertions fail, descendants survive, mounts
remain, or state is malformed. Do not compare Minibox with a production runtime as if the feature and
security sets were equivalent.

Potential hypotheses to test, not claimed conclusions, are that injected-backend runs isolate Python
control-plane overhead, rootfs traversal grows with path depth and search candidates, durable state
synchronization costs more than plain replacement, and namespace creation dominates this small
workload. Publish contrary observations rather than selecting only samples that fit those hypotheses.

