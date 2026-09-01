# Comprehension questions

Answer these in your own `COMPREHENSION_RESPONSES.md`. Use equations, short examples, or references to your own code and tests where useful. Do not use external course material.

1. Starting only from the forward divider equation in the brief, derive sensor resistance `R_s` as a function of `V_node`, `V_ref`, and `R_f`. State the domain on which your expression is defined and include units.

2. Explain what happens mathematically and operationally as `adc_count` approaches `M`. Why does the task reject equality instead of returning a very large number or infinity? Name one test that distinguishes those policies.

3. A stable rolling median can still be consistently wrong as a physical estimate. Give two distinct model or measurement errors that filtering cannot remove, and explain why.

4. Describe an invariant for your trailing-median implementation. Then give a short stream for which taking the median of all observations seen so far produces a different result from the required fixed trailing window after eviction.

5. Suppose a valid output file already exists and the next input has a malformed final row. Trace the relevant control and filesystem events in your implementation. What concrete evidence shows that the old bytes survive?

6. Identify one boundary example, one property that holds across many valid samples, and one integration behavior in your tests. Explain the different defect each is intended to detect.

7. The catalog snapshot calls one aggregate record “Assignments” and marks it as an official course unit, but only supplies two index URLs. What can a course manager safely claim from that evidence, and what additional evidence is needed before turning the record into graph units?

8. If the ideal sensor topology were reversed—sensor on top and the fixed resistor to ground—which parts of your software design should change and which should remain stable? Focus on separation of concerns rather than supplying replacement code.

