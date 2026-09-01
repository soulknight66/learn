# Debugging Log — Unit 0 Revision

This log records commands and externally observable results, not private
reasoning. It is limited to unit_kickoff_vmwalk_v1.

## D1 — Confirm the packaging failure

- Experiment: find . -maxdepth 3 -type f -print followed by sorting.
- Observation: the starting workspace contained the supplied materials,
  prior narrative files, feedback, and job metadata, but none of the required
  root-level implementation artifacts.
- Change: created a fresh implementation package at the submission root;
  nothing under LEARNER_MATERIAL/, PRIOR_ATTEMPT/, or EXAMINER_FEEDBACK/ was
  edited.

## D2 — First strict compilation

- Experiment: run make clean all after adding the initial C modules and
  ordinary build rules.
- Result: exit 2. The first compile command failed with
  "cc: error trying to exec 'cc1': execvp: No such file or directory".
- Observation: cc --version reported GCC 8.5.0, so the driver existed even
  though its backend lookup failed.

## D3 — Resolve only the local sealed-runner toolchain

- Experiments: query gcc -dumpmachine, gcc -dumpversion, and
  gcc -print-prog-name=cc1; inspect the corresponding local GCC directories
  and linker names.
- Observations: the target/version were x86_64-redhat-linux and 8; cc1 existed
  under /usr/libexec/gcc/.../8; GCC libraries and headers existed under
  /usr/lib/gcc/.../8; /usr/bin/ld.bfd existed, but ld did not.
- Change: the Makefile now derives the target/version paths when present and
  creates build/toolchain/ld as a symlink to the available local linker. No
  toolchain was downloaded and generated products stay under build/.
- Retest: ordinary make clean all returned 0.

## D4 — Behavioral checks

- Experiment: run make check.
- Initial result: all 15 initial black-box test methods passed.
- Follow-up change: added separately named checks for UNMAPPED and PERMISSION
  outcomes and made the CRLF test exercise uppercase hex digits.
- Coverage includes atomic no-output rejection, the exact 128/2,048/1,024
  bounds, 256 unique mappings, numeric overflow defense, exact formatting,
  all three exit statuses, and valid boundary forms.

## D5 — Documentation and qualification check

- Experiment: rerun make check after the two follow-up tests.
- Result: exit 0; all 17 test methods passed.
- Experiments: count DESIGN.md words and the words in each numbered
  comprehension section.
- Results: DESIGN.md contains 227 words; the eight response sections contain
  51, 56, 53, 42, 44, 51, 44, and 55 words, respectively.
- Evidence boundary: this qualification result is learner-generated. The
  final clean command outputs are copied without alteration into evidence/,
  and neither result is labeled HARNESS-VALIDATED.
