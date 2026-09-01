# DBG-2 answer

Rollback must clear every parent PTE published by this call, remove each newly
created zeroed table object, and deallocate the corresponding frame in reverse
creation order. It must leave pre-existing parent entries and tables untouched.
The root identity, table-frame count, free/allocated counts, translations, and
`validate` result must all match the pre-call snapshot.

Test a mapping requiring two intermediate tables with zero, one, and two free
frames after the root. The first two cases fail without residue; the third
succeeds. Repeat with zero, one, and two prefixes already present so each
possible allocation site becomes the failure point, and retry after each
failure to prove returned frames really are reusable.
