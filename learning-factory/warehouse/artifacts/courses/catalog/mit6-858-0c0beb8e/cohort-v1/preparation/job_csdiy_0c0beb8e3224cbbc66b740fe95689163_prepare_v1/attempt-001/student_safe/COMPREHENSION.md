# Comprehension Prompts

Answer these in your own words in `notes.md`. Tie each response to a concrete part of your design, test suite, or debugging evidence. These are questions only; the learner packet contains no answer key.

1. In the intended architecture, which values cross an untrusted boundary, and which values are assumed to have been established by trusted components? What can the demonstration CLI validate, and what can it never authenticate by itself?

2. Suppose an attacker can choose the CLI's `principal.role` field. Trace the resulting failure through the stated policy. What integration boundary would have to change before the core could safely protect a real service?

3. The policy has a finite 36-case product space. What does exercising every combination establish, and which important security properties does that exhaustive table still fail to establish?

4. Choose a request for which more than one rule might appear relevant. Explain why rule ordering and stable reason-code precedence matter for both correctness and operations. Point to a test that fixes the intended behavior.

5. Why keep strict parsing separate from the pure authorization function? Describe one parser defect that policy-only tests would miss and one policy defect that CLI-only tests could make hard to localize.

6. JSON permits implementations to disagree about duplicate member names. What security or operability problem could arise if two components interpret the same bytes differently? Show how your boundary test detects your chosen behavior.

7. A generic `invalid_input` response reveals less than a detailed parse error, but gives an operator less immediate context. How would you design safe internal diagnostics without echoing identifiers or allowing the external response to become an oracle?

8. Authorization uses resource ownership and tenant metadata, but a later component performs the actual operation. Describe a time-of-check/time-of-use failure that could occur if this metadata changes. What would need to be made atomic or revalidated in a real system?

9. Imagine adding a `support` role that may read a resource only while a time-limited support grant is active. Identify the new trusted data, state transition, failure mode, and tests you would require before extending the policy.

10. If an identity provider or metadata store is unavailable, what would fail-open and fail-closed behavior look like? Discuss both the security effect and the availability cost.

11. Review your `debugging-log.md`. Which observation changed your mental model rather than merely fixing syntax? What evidence supports that claim?

12. State precisely what completing this kickoff can demonstrate. List at least three claims it cannot support about production security, transfer to a different system, official MIT assignments, or completion of the full course.
