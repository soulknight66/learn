# Shell-injection review answer

The fragment collapses structured arguments into one shell program. Shell metacharacters, whitespace,
quotes, substitutions, redirects, and newlines in either `rootfs` or any command element become
syntax. For example, a single nominal argument containing `;` followed by a host-side marker command
can execute that marker outside the intended chroot. Joining also destroys the distinction between
one argument containing spaces and two arguments.

The repair is to keep every boundary structured: invoke `subprocess` with an argv list and
`shell=False`, pass a strict size-limited JSON helper payload on stdin, and validate the payload again
inside the helper. Apply a finite timeout, launch in a process group/session appropriate for cleanup,
capture bytes, and terminate/reap the complete child tree on failure. Rootfs selection must go through
the dedicated containment resolver rather than being accepted merely because it is one argv element.
A separate bounded status pipe, marked close-on-exec in the helper, should report readiness or setup
error so a target's nonzero exit is not confused with a launcher failure.

A regression test supplies metacharacters and whitespace as literal elements, injects a recording
backend, and asserts the exact argv and decoded payload. It also asserts that no host marker appears.
Test timeout and malformed-result paths separately.

Avoiding the host shell does not forbid a caller from explicitly choosing an in-container command
such as `/bin/sh -c ...`; in that case the shell is the requested target and its script remains one
literal argv element. Nor does argv construction solve rootfs races, excess privilege, inherited file
descriptors, unbounded output, or descendant cleanup. Those require separate controls.
