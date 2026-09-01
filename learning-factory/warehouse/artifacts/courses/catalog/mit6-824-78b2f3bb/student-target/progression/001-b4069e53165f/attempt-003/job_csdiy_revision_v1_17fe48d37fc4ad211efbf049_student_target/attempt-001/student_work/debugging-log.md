# ParcelQ revision debugging log

Provenance: commands below were executed in this bounded workspace. Results are
actual local observations unless explicitly labeled as the prior examiner's
published observation. This is a debugging record, not private reasoning.

The shell repeatedly printed unresolved numeric user/group-name warnings before
commands. They are environmental startup diagnostics and did not alter the
reported Python exit statuses.

## 1. Scoped input and artifact inventory

Initial command from the attempt root:

~~~bash
pwd
rg --files ASSIGNMENT PRIOR_ATTEMPT EXAMINER_FEEDBACK student_work 2>/dev/null | sort
~~~

Observation: pwd printed the provided attempt root, but rg printed no paths, so
that listing was inconclusive. I followed with:

~~~bash
ls -la
find ASSIGNMENT PRIOR_ATTEMPT EXAMINER_FEEDBACK student_work \
  -maxdepth 2 -type f -print 2>/dev/null | sort
~~~

Observation: ASSIGNMENT, PRIOR_ATTEMPT, and EXAMINER_FEEDBACK existed;
student_work did not. The read-only prior attempt contained only notes.md,
submission.md, debugging-log.md, and self-check.md.

Published prior-examiner observation: the staged learner inventory likewise
lacked lease_queue.py, test_lease_queue.py, DESIGN.md, and INCIDENT.md. Its
clean bounded test exited 1 with:

~~~text
ModuleNotFoundError: No module named 'test_lease_queue'
~~~

Revision: create the core executable and evidence artifacts themselves instead
of repeating their claimed presence in prose.

## 2. Runtime observation

Command:

~~~bash
python3 --version
command -v python3
~~~

Actual output:

~~~text
Python 3.6.8
/usr/bin/python3
~~~

Revision consequence: immutable records use typing.NamedTuple rather than
features added after Python 3.6.

## 3. First compile and full suite

Working directory: student_work.

~~~bash
python3 -m py_compile lease_queue.py test_lease_queue.py
python3 -B -m unittest -v test_lease_queue.py
~~~

Both commands exited 0. The unittest summary was:

~~~text
Ran 20 tests in 0.003s

OK
~~~

All ten ParcelQContractTests, six ParcelQPublicTraceTests, and four
UnsafeExcerptIncidentTests reported ok; no test was skipped. There was no red
implementation test in this first materialized run, so no failed local test is
being rewritten as a success.

## 4. Focused incident experiments

Command:

~~~bash
python3 -B -m unittest -v test_lease_queue.UnsafeExcerptIncidentTests
~~~

Actual summary and status:

~~~text
Ran 4 tests in 0.000s

OK
~~~

Here OK means all four tests observed the deliberately unsafe transcription's
expected defect: stale mutation before fence rejection, duplicate transition
execution, conflicting-payload mutation hidden by ID-only replay, and an
invented higher epoch self-authorizing. INCIDENT.md preserves the individual
commands and revisions.

I also executed the deterministic two-job trace printed in INCIDENT.md. Its
selected JSON contained:

- a tick-4 REPLAY with presented old/1, active new/2, saved response
  OK_CLAIMED, equal before/after CLAIMED state, and both mutation flags false;
- a tick-4 FENCED result with presented old/1, active new/2, equal before/after
  READY state, and both mutation flags false.

The command exited 0. The actual records are preserved in INCIDENT.md rather
than paraphrased as a behavioral claim.

## 5. Fresh-copy reproduction of the packaging condition

After all eight submitted files existed, I created a new directory from the
attempt root:

~~~bash
mktemp -d ./.revision-cleancheck.XXXXXX
~~~

It returned ./.revision-cleancheck.Wbpgya. I copied the files by explicit name:

~~~bash
cp student_work/lease_queue.py student_work/test_lease_queue.py \
  student_work/DESIGN.md student_work/INCIDENT.md \
  student_work/notes.md student_work/submission.md \
  student_work/debugging-log.md student_work/self-check.md \
  .revision-cleancheck.Wbpgya/
~~~

From that new directory I ran:

~~~bash
find . -maxdepth 1 -type f -printf '%f\n' | sort
env -u PYTHONPATH python3 -B -m unittest -v test_lease_queue.py
~~~

The inventory printed exactly DESIGN.md, INCIDENT.md, debugging-log.md,
lease_queue.py, notes.md, self-check.md, submission.md, and
test_lease_queue.py. The test process exited 0:

~~~text
Ran 20 tests in 0.003s

OK
~~~

The use of -B prevented bytecode generation, and removing PYTHONPATH prevented
an external module path from making the local import pass accidentally. This
was a local reproduction in a new directory, not independent worker-harness
validation.

## 6. Current limitations and next diagnostic

The known published packaging failure is preserved above. Current local checks
cannot establish what an independent orchestrator will stage or validate. The
implementation intentionally has no evidence for real-clock behavior,
concurrent processes, persistence or restart, coordinator failover,
replication, hostile credentials, or network/storage faults.

If this bounded model were extended under a separate task, the next useful
diagnostic would enumerate short event prefixes and mechanically check the
authority, state, and history invariants after every prefix. Production-facing
work would then need durable crash-consistency and concurrent-process evidence.
Neither extension nor transfer verification was attempted here.
