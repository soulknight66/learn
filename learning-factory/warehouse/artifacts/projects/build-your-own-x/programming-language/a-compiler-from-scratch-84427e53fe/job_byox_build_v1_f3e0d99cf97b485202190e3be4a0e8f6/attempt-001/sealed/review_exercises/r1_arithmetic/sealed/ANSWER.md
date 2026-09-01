# R1 answer

Reject booleans and require two integers; reject zero divisors; compute quotient by truncating toward zero rather than relying on Ruby integer `/`; derive remainder as `a - q*b`; and range-check every result. In particular, `MIN_INT / -1` overflows even though both operands are valid. Pop order must preserve left versus right, and underflow must be diagnosed before arithmetic.
