# Unit 0 Revision Notes

## Scope and status boundary

These notes cover only unit_kickoff_vmwalk_v1. The artifact is a C11 teaching
model, not xv6, Sv39, an MIT lab, or evidence of completing MIT 6.S081.
Learner checks are labeled SELF-CHECKED; controlled validation remains the
worker harness's responsibility.

## Feedback addressed

The examiner found that the earlier package contained only narrative claims:
the described source, Makefile, tests, design answers, and evidence were
absent. This revision adds the actual implementation and every path required
by the study task. The revised submission text points only to files that are
present, and the evidence is regenerated from this workspace.

## Contract decisions implemented

- A 16-by-16 table stores presence separately from the PPN and rwx bits.
- Up to 1,024 parsed accesses are retained until end-of-file validation, so a
  bad later line cannot leave partial standard output.
- The byte reader distinguishes LF, CRLF, and an allowed unterminated final
  line while enforcing 128 bytes and 2,048 logical lines.
- Hexadecimal accumulation is checked before multiplication/addition against
  each field's maximum.
- Modeled faults remain valid status-0 results; invalid invocation or trace
  input returns 2, and file/resource failures return 1.

## Concrete experiments and observations

1. Inventorying the initial revision workspace showed no Makefile, src/,
   tests/, design response, comprehension response, or evidence directory.
2. The first strict build reached cc but failed because the sealed runner's
   driver could not locate cc1. GCC queries located version-derived helper and
   library directories, and /usr/bin/ld.bfd was present without the usual ld
   name.
3. After the Makefile derived those local paths and created a build-local
   linker symlink, make clean all returned 0 with
   -std=c11 -Wall -Wextra -Werror -pedantic.
4. The black-box suite exercises exact translations, both modeled faults, all
   access modes, aliases, malformed fields, atomic rejection, line and access
   maxima, a fully populated table, invocation errors, and missing files. The
   final outcomes are preserved in evidence/test.log.

## Remaining authority

No independent controlled fixture result or transfer verification is claimed
here. A harness failure must override these learner observations and keep the
unit unvalidated.
