# D2 answer

Ruby's `%` uses a floor-division remainder, whose sign follows the divisor. Pebble specifies truncation toward zero and a remainder whose sign follows the dividend. Compute `q` from absolute magnitudes with the combined sign, then compute `r = a - q * b`. For `a = -7`, `b = 3`, this yields `q = -2`, `r = -1`, and preserves `a == q*b + r`.
