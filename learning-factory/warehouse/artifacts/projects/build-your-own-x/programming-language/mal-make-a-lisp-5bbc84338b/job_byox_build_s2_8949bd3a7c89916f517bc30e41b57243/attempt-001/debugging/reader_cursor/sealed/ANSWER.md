# Diagnosis

The escape branch advances `index` by two source characters but `column` by one. For example, after a
valid two-character escape, a later invalid escape is reported one column early. Advance the column by two
in that branch. A regression should include at least one valid escape followed by an invalid one and assert
the invalid backslash's one-based column; a separate successful case should confirm decoded content so a
fix cannot simply skip both characters.
