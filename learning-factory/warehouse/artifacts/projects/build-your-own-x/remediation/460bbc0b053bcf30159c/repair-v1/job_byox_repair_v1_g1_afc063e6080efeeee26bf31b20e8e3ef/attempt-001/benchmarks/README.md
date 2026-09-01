# Benchmark design

No benchmark claim is made for this generated artifact. Fixed table sizes make latency less important
than predictable upper bounds, and host timings would not represent a real kernel target.

If extending the lab, measure scheduler selection, page mapping, and name lookup across every supported
occupancy. Record the compiler, flags, host, timer, warm-up policy, raw samples, and a baseline. Do not
label those measurements as emulator or hardware performance.
