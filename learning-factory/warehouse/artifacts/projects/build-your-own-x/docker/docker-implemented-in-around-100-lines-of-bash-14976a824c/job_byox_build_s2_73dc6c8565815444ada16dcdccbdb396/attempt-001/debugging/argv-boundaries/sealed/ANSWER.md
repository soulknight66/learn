# Sealed diagnosis

The scalar cannot encode Bash's argument boundaries without inventing a serialization and parser.
Unquoted expansion additionally performs word splitting and pathname expansion. Quoted scalar
expansion has the opposite error: it turns the entire command into one argument.

Keep the post-`--` operands in the positional-parameter array. After `shift 2`, invoke the runner as
`"$runner" "$rootfs" "$name" "$@"`; after the runner shifts its metadata operands, execute the
container command as `exec ... -- "$@"`. At no stage use `eval`, `sh -c`, or an interpolated command.

The regression runner should compare argument count and each indexed value directly. Its expected
tail is four distinct values: `two words`, `*`, `semi;colon`, and the empty string.
