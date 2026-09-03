# Debugging answer

The check compares characters rather than path components. Both `root-other` and `root-outside`
start with the characters in `root`, so traversal and an existing symlink can resolve to a sibling
while still passing. Canonicalize the trusted root, reject parent components, resolve the candidate,
then call `candidate.relative_to(root)` and treat `ValueError` as escape.

That repair still has a time-of-check/time-of-use race: another process can rename or replace a
component after `resolve` and before use. A production repair pins a root directory descriptor and
uses descriptor-relative resolution such as `openat2(RESOLVE_BENEATH|RESOLVE_NO_MAGICLINKS)`.
