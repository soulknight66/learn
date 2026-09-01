# Comprehension prompts

Answer in your own words and refer to concrete decisions or tests in your implementation. This file contains questions only; it does not contain solutions.

1. State the conditions that make your walk depth-first pre-order. Where in your design is sibling order fixed?

2. Give one plausible implementation mistake that would visit every node but still violate the required order. Which test would reveal it?

3. What responsibility belongs to traversal, and what responsibility belongs to outline rendering? Describe a future change that your separation makes easier.

4. How does your ownership and borrowing design avoid unnecessary cloning? What would change if an external compiler library owned all nodes and exposed only borrowed references?

5. When a new expression variant is introduced, which compiler or test signals should force the implementation to address it? Identify any place where the new variant could be silently missed.

6. Explain how an output error travels from the point of failure to the caller. Why is a panic a poor default for that path?

7. Why is exact-output testing useful here, and what behavior should be tested structurally instead of only through a large snapshot?

8. Describe a generated-tree or fuzzing strategy for this component. How would you bound depth and size, and what properties would serve as the oracle?

9. List three facts you would need to inspect before integrating this design with KECC or another real compiler AST. For each, name the risk of guessing.

10. What does successful completion of this exercise demonstrate, and what does it explicitly not demonstrate about the wider CS420 course?
