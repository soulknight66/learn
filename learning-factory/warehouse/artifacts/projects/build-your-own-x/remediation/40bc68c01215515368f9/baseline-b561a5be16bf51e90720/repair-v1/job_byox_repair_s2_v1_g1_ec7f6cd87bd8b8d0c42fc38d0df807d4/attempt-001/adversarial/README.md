# Adversarial validation prompts

Validator-only prompts (no answers): try deeply nested parentheses/blocks, enormous literals, invalid
escape endings, jump targets at `-1` and `code.size()`, constant indexes of the wrong type, stack
underflow at every consuming opcode, assignment across three scopes, redeclaration with a failing
initializer, negative zero division, and loops whose condition becomes the wrong type. Confirm every
case becomes a controlled `MicaException` or a documented host resource boundary.
