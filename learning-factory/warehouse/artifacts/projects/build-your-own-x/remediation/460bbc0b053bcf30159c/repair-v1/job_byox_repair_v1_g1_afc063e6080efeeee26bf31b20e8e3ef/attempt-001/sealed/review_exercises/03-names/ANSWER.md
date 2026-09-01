# Filesystem-name review findings

Name validation scans at most `MICA_NAME_MAX + 1` input bytes. It rejects empty strings, embedded path
separators, and inputs without a terminator in that window. Stored names always include a terminator,
and comparisons are bounded, so a full-length valid name cannot alias an unterminated input.

The flat namespace intentionally has no `.` or `..` semantics. Adding directories would require a
component parser rather than relaxing this validator.
