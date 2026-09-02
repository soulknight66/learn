# Pipeline review answer

The slice operation panics if a nonconforming tokenizer ever returns no tokens;
more importantly, it deliberately removes the required EOF token, so every
successful tokenization becomes an invalid parser input. The formatted lexer
error uses `%s`, flattening `*StageError`; `errors.As` can no longer recover it.

Do not alter the returned token stream. Return phase errors unchanged, or wrap
with `%w` only when context is genuinely needed. Tests should exercise empty and
valid source, assert EOF reaches `Parse`, inject/observe a lexical `StageError`
through `Execute`, and use `errors.As` to confirm the stage and span survive.
