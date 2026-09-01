# Course kickoff: from ADC counts to a tested sensor pipeline

## What this unit is

This is a bounded, simulation-only kickoff inspired by the subject area described in the CSDIY catalog entry for **UCB EE16A&B: Designing Information Devices and Systems I&II**. It is a course-manager-authored bridge for a learner who already handles algorithms comfortably and now wants to practice building dependable software around a small physical model.

It is not an official UC Berkeley unit, does not reproduce an EE16 assignment, and is not evidence that you have completed EE16A, EE16B, or the roughly 150-hour catalog course. Plan for about 6–10 hours, with 8 hours as the target.

All required material is in this learner-safe bundle. The catalog listed course sites, notes, playlists, and assignment indexes, but their contents were not retrieved or verified for this kickoff. You do not need them and should not depend on them.

## The engineering story

A resistive sensor can be placed in a voltage divider so that changing resistance changes a voltage. An analog-to-digital converter (ADC) turns that voltage into an integer count. Production software then has to parse observations, reject impossible or ambiguous states, convert units, reduce noise, preserve data ordering, and write durable output.

The mathematics is small. The engineering surface is not. A trustworthy implementation needs explicit assumptions, useful errors, stable numeric formatting, boundary tests, and a policy that does not destroy an earlier good result when new input is bad.

This unit uses only idealized data. Do not construct or connect physical hardware for it. In particular, do not work with mains power or unknown circuits.

## Minimal circuit model

Use these ideal definitions:

- Voltage is electrical potential difference, measured in volts (V).
- Current is the rate of charge flow, measured in amperes (A).
- Resistance describes opposition to current, measured in ohms (Ω).
- Ohm’s law for an ideal resistor is `V = I R`.
- Kirchhoff’s current law says the signed currents at an ideal node sum to zero.

For this unit, a fixed resistor `R_f` connects the reference supply `V_ref` to a measured node. The unknown sensor resistance `R_s` connects that node to ground:

```text
V_ref --- R_f ---+--- R_s --- ground
                 |
               V_node
```

The ideal forward relation is:

```text
V_node = V_ref * R_s / (R_f + R_s)
```

An ideal ADC reports a count `c` relative to its full-scale count `M`:

```text
V_node = (c / M) * V_ref
```

Real components have tolerances, self-heating, quantization, electrical noise, reference error, and ADC nonlinearity. Those effects are deliberately outside this first model. Your documentation must avoid implying that ideal converted values are calibrated physical truth.

## Median filtering

A trailing rolling median replaces each raw converted resistance with the median of the most recent observations, up to a fixed window size. Unlike a mean, a median is resistant to a small number of extreme observations. Unlike sorting the entire dataset, a trailing window preserves a local, causal view of a changing stream.

Filtering does not repair a wrong topology, a wrong reference voltage, a saturated ADC, or a biased sensor. It only applies the precisely stated transformation to accepted values.

## Outcomes

By the end of the kickoff, you should be able to:

1. derive an inverse conversion from the supplied forward model and identify its singular boundary;
2. separate domain validation from CSV and command-line concerns;
3. implement a deterministic trailing-median transformation without reordering samples;
4. use automated tests to pin down ordinary, boundary, malformed, and failure-path behavior;
5. write output atomically enough that bad input cannot clobber an earlier valid artifact; and
6. distinguish evidence from inference when describing source material and software behavior.

## Boundaries and completion

Completing the implementation and comprehension work can count only toward this kickoff unit after independent validation. It cannot complete the catalog course. Later expansion would require verified materials, a provenance-backed unit sequence, and separate validation evidence.

