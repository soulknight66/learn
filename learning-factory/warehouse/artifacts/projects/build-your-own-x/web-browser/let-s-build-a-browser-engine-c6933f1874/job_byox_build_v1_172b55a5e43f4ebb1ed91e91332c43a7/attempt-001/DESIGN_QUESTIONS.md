# Design questions

Write down your choices before implementation.

1. Which type owns raw bytes, and at what exact point is UTF-8 required?
2. How will you detect the header delimiter without scanning beyond the header budget?
3. Why can accepting both Content-Length and Transfer-Encoding create ambiguity?
4. At which operation will node and depth budgets be charged?
5. What parser state makes a mismatched closing tag easy to report?
6. What total ordering will choose between competing CSS declarations?
7. Which properties inherit, and how will text nodes receive inherited values?
8. Define whether each rectangle edge is inclusive or exclusive.
9. How will wrapping behave when one word is wider than the viewport?
10. What checked arithmetic is required before calling the transport?
11. Which policies would a real DNS/TCP transport need to prevent server-side request forgery?
12. What intentionally unsupported behavior should fail closed rather than be guessed?
