# Comprehension Questions

Answer these in `submission/comprehension.md`. Show reasoning where requested. This file contains questions only.

1. Define the sample space for one trial. Which independence and distribution assumptions make your exact calculation valid?

2. Derive the probability of at least one collision without beginning from a simulation. Explain how your expression changes across the boundary cases `draws <= 1` and `draws > buckets`.

3. Identify two numerical problems that a direct implementation of the mathematical expression can encounter at large input sizes. How does your implementation reduce them, and what limitations remain?

4. What random variable is averaged by the Monte Carlo estimator? Derive its expectation and variance, then explain the interval method you chose.

5. Why is an explicit seed useful but insufficient by itself as a complete reproducibility record? Name at least three additional facts another developer needs.

6. Describe how to test randomized code without making the normal test suite flaky. Distinguish a deterministic property test from a statistical validation test and give one example of each from your work.

7. Suppose an exact value falls outside one reported 95% interval. What conclusions are justified, what conclusions are not justified, and what diagnostic steps would you take next?

8. The implementation assumes uniform independent bucket choices. If production traffic is skewed or correlated, which parts of the API, model, test strategy, and experiment record would need to change?

9. Explain why injecting a random-number generator improves modularity compared with reading module-global random state. Include one concurrency or test-isolation consequence.

10. What failure can occur if a process is interrupted while overwriting a JSON result directly? Explain the observable contract provided by your chosen safe-write strategy.
