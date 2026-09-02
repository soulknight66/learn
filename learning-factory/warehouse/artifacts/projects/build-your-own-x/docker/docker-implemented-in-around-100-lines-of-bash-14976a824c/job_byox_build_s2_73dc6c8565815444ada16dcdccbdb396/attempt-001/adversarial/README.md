# Adversarial test inventory

Adversarial checks are sealed because edge-case expectations can reveal implementation strategy.
The runnable controller cases are in `sealed/reference_tests/test_adversarial.sh` and cover:

- state-layout and container symlink substitution;
- symlinked metadata;
- traversal-shaped, absolute, empty, and overlong names;
- shell metacharacters and whitespace retained as argv data;
- refusal to alter an out-of-state sentinel.

These are targeted regression cases, not fuzzing and not a security certification.
