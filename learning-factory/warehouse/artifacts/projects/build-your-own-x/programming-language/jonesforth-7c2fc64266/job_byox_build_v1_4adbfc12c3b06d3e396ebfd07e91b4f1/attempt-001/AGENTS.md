# Agent instructions for this challenge

The learner-visible set is README.md, AGENTS.md, MANIFEST.yaml, REQUIREMENTS.md, CONCEPTS.md,
DESIGN_QUESTIONS.md, starter/, public_tests/, and environment/. Treat all other paths as harness
or provenance material and do not inspect them. Edit implementation work only beneath starter/;
MANIFEST.yaml is visible metadata and must remain unchanged.

Implement the contract in starter/stackvm.S. Preserve the executable name stackvm and the existing
Makefile interface. You may add learner-authored files beneath starter/ and public_tests/, but do
not add copied upstream code, credentials, generated binaries, or solution directories.

Use these deterministic checks from the repository root:

    make -C starter clean all
    python3 -m unittest discover -s public_tests -v

Do not weaken or delete a test to make a result pass. Record assumptions in your own notes and use
DESIGN_QUESTIONS.md to review decisions about parsing, VM state, and error atomicity.
