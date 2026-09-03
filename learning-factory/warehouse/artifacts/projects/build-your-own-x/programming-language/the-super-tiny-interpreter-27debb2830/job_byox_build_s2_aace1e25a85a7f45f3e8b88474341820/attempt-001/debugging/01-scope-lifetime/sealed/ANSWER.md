# Instructor answer

The common defects are implementing `EXIT_SCOPE` by clearing the whole scope stack or implementing
`DEFINE` against the global map. `ENTER_SCOPE` must append one fresh map, `DEFINE` must touch only
the last map, and `EXIT_SCOPE` must remove exactly that last map while refusing to remove globals.
The operand result is on a separate stack and must survive scope exit. Assignment is different from
definition: it searches inward-to-outward and updates the first existing name.
