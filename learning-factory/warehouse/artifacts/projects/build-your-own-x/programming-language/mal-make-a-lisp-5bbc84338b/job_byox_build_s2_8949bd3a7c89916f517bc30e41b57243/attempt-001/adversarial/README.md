# Adversarial test prompts

After ordinary examples pass, build tables around boundaries: every escape at end of input, comments next
to delimiters, unmatched punctuation, reserved words embedded in symbols, booleans in integer built-ins,
duplicate parameters, falsey branch selection, callable equality, zero division, and attempts to call
data. Also test a 5,000-step tail recursion and confirm the host recursion limit is unchanged.

No expected implementation or answer is provided here. Derive assertions from `REQUIREMENTS.md`.
