# Debugging challenge: intermittent JSON rejection

Under some client/network timings, PUT requests return a JSON error or appear to leave bytes
for the next request. Sending the same bytes in one local write often succeeds. The failure is
reproducible without external network access:

```sh
PYTHONPATH=debugging/partial-body/buggy python3 debugging/partial-body/regression.py
```

Investigate byte-stream assumptions, capture the smallest failing split, and add a regression
before revealing `sealed/`. This challenge has one intentional root cause; do not “fix” it by
adding sleeps or changing the advertised body length.
