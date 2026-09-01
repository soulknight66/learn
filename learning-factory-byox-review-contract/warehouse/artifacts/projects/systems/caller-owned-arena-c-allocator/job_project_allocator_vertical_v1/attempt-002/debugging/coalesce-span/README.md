# Debugging challenge: corrupted physical span

The allocator builds and simple allocate/free use can appear normal, but freeing two adjacent
blocks makes `lf_check` report corrupt metadata. There is exactly one intentional source-code
mutation. Reproduce the failure, draw the arena/header/payload layout, identify the violated
invariant, add the smallest regression, and repair it before opening `sealed/`.
