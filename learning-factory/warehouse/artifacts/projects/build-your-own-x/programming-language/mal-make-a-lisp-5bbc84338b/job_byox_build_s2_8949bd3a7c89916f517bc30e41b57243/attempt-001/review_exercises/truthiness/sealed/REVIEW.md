# Review answer

The candidate delegates to Python truthiness. Pebble makes only `false` and `nil` falsey, while Python also
treats integer zero, the empty string, and the empty list as false. Minimal counterexamples place each in an
`if` condition and expect the consequent, such as `(if 0 1 2)`, `(if "" 1 2)`, and `(if '() 1 2)`.
Identity checks (`value is None or value is False`) express the specified negative predicate without
accidentally accepting additional host values.
