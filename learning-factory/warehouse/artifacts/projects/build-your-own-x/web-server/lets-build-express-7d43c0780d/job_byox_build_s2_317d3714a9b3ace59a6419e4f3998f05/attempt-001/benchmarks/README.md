# Benchmark harness

`http-load.js` is a small dependency-free loopback harness. It emits raw JSON measurements; it does
not define an acceptance threshold and has not been run on this build host.

Start a candidate server separately, then run:

```sh
TARGET_URL=http://127.0.0.1:3000/health DURATION_MS=5000 CONCURRENCY=16 \
  node benchmarks/http-load.js
```

The harness refuses non-loopback targets. Record the exact Node version, host, candidate commit,
route table, command, warmup policy, raw output, and resource measurements before drawing a
conclusion. No benchmark label is warranted by merely including this script.
