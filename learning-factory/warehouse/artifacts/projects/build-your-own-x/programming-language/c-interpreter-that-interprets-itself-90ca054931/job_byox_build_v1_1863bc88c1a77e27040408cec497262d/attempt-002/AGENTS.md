# Agent guide for the Mini-C challenge

Work only in this challenge repository. Do not retrieve or copy the linked provenance
resource. Learner-visible files are the root learning documents plus `starter/`,
`public_tests/`, and `environment/`. Keep implementations, answers, private tests, and
solution-bearing reviews below `sealed/`.

The language contract in `REQUIREMENTS.md` is authoritative. Preserve deterministic limits,
diagnostics, and exit statuses. Use C11, argv-style subprocess invocation, bounded execution,
and captured output. Do not claim that the language is ISO C or that the staged bootstrap is a
full source-level self-host.

Before changing semantics, add a black-box test. A learner submission should be checked with:

```sh
make -C starter
python3 public_tests/run_tests.py starter/build/minic
```

The uncompleted starter is expected to build but not yet pass behavioral tests. Independent
validation—not an agent's report—controls all completion labels.
