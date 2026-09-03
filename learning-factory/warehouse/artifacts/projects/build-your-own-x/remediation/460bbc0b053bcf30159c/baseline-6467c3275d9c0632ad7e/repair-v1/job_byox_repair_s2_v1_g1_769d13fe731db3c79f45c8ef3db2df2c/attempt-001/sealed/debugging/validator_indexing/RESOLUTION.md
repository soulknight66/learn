# Validator indexing resolution

The inode index must be checked for both lower and upper bounds before it appears in any array
expression. In C, a left-to-right `||` chain short-circuits, so bounds predicates can precede the
inode-use and cursor predicates. Sanitized tests should try -1, `CAIRN_MAX_FILES`, and a large positive
value in otherwise valid copies.
