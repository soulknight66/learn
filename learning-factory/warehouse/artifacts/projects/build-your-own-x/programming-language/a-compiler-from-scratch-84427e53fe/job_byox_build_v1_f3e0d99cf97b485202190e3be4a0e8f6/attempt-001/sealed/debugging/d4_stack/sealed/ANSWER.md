# D4 answer

The condition expression pushes one boolean and `JUMP_IF_FALSE` must consume it on both the taken and fall-through paths. Every statement in the body has net stack effect zero, and `JUMP` changes only the instruction pointer. If the conditional jump merely peeks, each iteration retains one boolean. A control-flow stack-height analysis should assign the same height to the loop header from initial entry and back-edge.
