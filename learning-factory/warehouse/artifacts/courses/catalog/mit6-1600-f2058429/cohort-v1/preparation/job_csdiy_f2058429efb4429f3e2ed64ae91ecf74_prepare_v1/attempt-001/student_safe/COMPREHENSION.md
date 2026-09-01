# Comprehension Prompts

Answer these in `COMPREHENSION_RESPONSES.md`. Keep each response under 150 words. Reason from your own artifact; when requested, name a function, invariant, or test that provides evidence.

1. Draw or describe the trust boundary for your component. Which data crosses it during enrollment and verification, and which actor or subsystem do you deliberately leave outside it?

2. Suppose an attacker obtains a copy of every stored credential record but cannot execute code in your process. What can the attacker attempt offline, and which two record fields change the cost or reuse of that attempt? Connect your answer to one invariant in your design.

3. Why would replacing the password derivation with one direct SHA-256 call change the attack economics even if the digest is never leaked through the API? Identify the test or review check that prevents that substitution in your artifact.

4. What property does `hmac.compare_digest` improve in your verification path? Name two timing or information leaks that it does not solve for the component as a whole.

5. Trace the unknown-user path and the wrong-password path in your implementation. What observable result is deliberately shared, where might the paths still differ, and what deterministic test supports your claim?

6. Your tests control a source of random bytes. Explain why that improves test evidence and what design mistake would make the production configuration unsafe. Point to both the production default and one deterministic test.

7. Choose one malformed-record case. Explain why failing closed is preferable to recovery by guessing, and identify the exact assertion that shows the failure cannot authenticate a user.

8. Imagine a future policy raises the required work factor. What record and API design choices help migration, and what behavior would need new implementation and tests? Keep the answer within the stated in-memory scope.

9. Give one claim that your passing unit tests justify and one security claim they cannot justify. For the second claim, describe a different kind of evidence that would be needed.
