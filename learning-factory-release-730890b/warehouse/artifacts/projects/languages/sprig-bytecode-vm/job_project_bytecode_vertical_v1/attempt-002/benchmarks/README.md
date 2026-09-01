# Benchmark protocol

Three unrecorded warmups precede raw `perf_counter_ns` samples. Each architecture runs in a
separate fresh Python process and must produce the same checksum-identified answer. Timings
cover the public `run_source` path, including lex/parse in both and compilation in bytecode;
they do not isolate dispatch. JSON captures parameters, command, host, raw samples, and summaries.
