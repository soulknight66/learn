# Review 2: ownership of a lifecycle record

`candidate.sh` is a proposed helper for recording one active run. Review it
under concurrency, signals, abrupt process death, and PID reuse. Assume the
called isolator is honest but may return any status.

Your review should describe an ownership rule for removing a run record and a
way for `ps` to distinguish a live owner from a recycled PID. Also address
what the trap changes globally and which exit status the function returns.

