# Design questions

Write down your answers before changing an interface. There is no answer key
in learner-visible material.

1. Which invariant ensures that at most one process is running, and at which
   lines in each transition is that invariant temporarily at risk?
2. If all processes are blocked, where should the scheduler remember its
   cursor so the first wakeup is treated fairly?
3. Why does reaping need to be separate from exiting? What information would
   be lost if exit immediately freed the slot?
4. Why are virtual-page alignment and physical-frame alignment checked
   independently?
5. Should two virtual pages be permitted to alias one physical frame? Which
   useful mechanisms and which hazards follow from that choice?
6. What is the difference between validating a permission mask and satisfying
   it?
7. How can `offset + count <= capacity` be rewritten so unsigned overflow
   cannot make an invalid write appear valid?
8. Does a zero-length write beyond end of file extend a file? Defend your
   interpretation using the published contract.
9. Which operations would need locks if two CPU cores could call these APIs?
   Identify the smallest useful lock scopes.
10. What must change to replace the linear filesystem lookup with a directory
    tree while preserving atomic error behavior?
