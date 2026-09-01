# Comprehension Check

> Artifact classification: learner-safe questions only  
> Validation label: unanswered assessment prompts  
> Provenance: course-manager-authored for `managed_unit_01_expression_front_end`

Answer in `RESPONSES.md` after the implementation is working. Use your own words and cite at least one relevant rule, class, method, or test name in each response. Keep the complete response under 1,200 words.

1. What information does your ANTLR parse tree contain that your printed AST intentionally omits? Why is that omission useful to a later compiler phase?

2. For `alpha - beta - gamma * -delta`, describe the root and child structure your program produces. Which grammar decisions establish that structure?

3. Why must the start rule require end-of-file? Give one input that a parser could otherwise accept only as a valid prefix, and identify the test that prevents this regression.

4. Give one lexical-error input and one syntax-error input that begin with the same valid token. Explain where each is detected and how your application prevents partial AST output.

5. Where is operator associativity represented in your implementation? Explain why precedence alone is not enough to determine the tree for a chain of subtraction or division.

6. What problem is prevented by pinning compatible ANTLR generation and runtime versions? Explain how a clean build demonstrates that generated files are build products rather than hidden local prerequisites.

7. Choose exponentiation as a possible right-associative extension. Identify the grammar, AST, and test-suite changes it would require, without implementing it. Name one interaction with unary negation that the language designer would have to decide.

8. Identify the highest-value negative test in your suite. State the specific false implementation it distinguishes from a correct one and why an ordinary valid example would not expose that defect.

These questions assess reasoning about your own artifact. They do not extend the implementation scope, and completing them does not imply completion of any later compiler topic.
