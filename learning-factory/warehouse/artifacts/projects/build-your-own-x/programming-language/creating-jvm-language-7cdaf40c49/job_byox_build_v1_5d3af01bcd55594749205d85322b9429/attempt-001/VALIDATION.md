# Validation record

Status remains `GENERATED` + `PARTIAL`. Independent validation is required. This
record contains observations from the generation host on 2026-08-31; it does not
self-award any build, test, fuzz, benchmark, review, transfer, or production
label.

## Host capability

Command:

```bash
java -version
```

Observed exit status: `127`.

```text
/bin/bash: java: command not found
```

A filesystem search of `/usr`, `/opt`, and `/arm/tools` found no `java` or
`javac` executable. `javalang` was also absent from the installed Python modules.
No dependency was downloaded or substituted.

## JSON and manifest checks

Command:

```bash
python3 -c 'import json; json.load(open("MANIFEST.yaml", encoding="utf-8")); json.load(open("PROVENANCE.json", encoding="utf-8")); print("JSON parse: PASS")'
```

Observed exit status: `0`; output: `JSON parse: PASS`.

Command:

```bash
python3 -c 'import json; d=json.load(open("MANIFEST.yaml")); assert set(d)=={"independent_validation","productionized","project_id","provenance_sha256","schema_version","source_commit","source_id","status","validation_labels"}; assert d["status"]=="GENERATED" and d["validation_labels"]==["GENERATED","PARTIAL"] and d["productionized"] is False; print("manifest invariant check: PASS")'
```

Observed exit status: `0`; output: `manifest invariant check: PASS`.

## Java build/test attempts

Command:

```bash
./environment/run-public-tests.sh
```

Observed exit status: `127`; output:

```text
BLOCKED: javac is required (JDK 17+)
```

Command:

```bash
./sealed/run-reference-tests.sh
```

Observed exit status: `127`; output:

```text
BLOCKED: javac is required (JDK 17+)
```

Command:

```bash
./sealed/run-benchmark.sh
```

Observed exit status: `127`; output:

```text
BLOCKED: java and javac are required (JDK 17+)
```

Therefore no Java source was compiled, no generated class was loaded, no test
was observed passing, and no benchmark measurement exists on this host.

## Static source sanity check

A read-only Python scanner walked every `*.java` file, ignored comments and
quoted literals, and checked delimiter balance plus unterminated string, char,
and block-comment states.

Observed exit status: `0`; output:

```text
Java delimiter/string static scan: PASS
```

This is only a text sanity check and is not evidence that Java compilation
succeeds.

A separate read-only Python check verified that Java package declarations match
their paths and that each public type matches its filename. Observed exit status:
`0`; output: `Java package/public-type static check: PASS`. This also is not a
compiler substitute.

Command:

```bash
sh -n environment/run-public-tests.sh sealed/run-reference-tests.sh sealed/run-benchmark.sh
```

Observed exit status: `0` (`shell syntax check: PASS` was printed by the wrapper).

## Structure, metadata, and credential checks

A read-only `pathlib` check evaluated the authoritative required and forbidden
path lists, followed by a recursive file-type check. Observed exit status: `0`;
output:

```text
required path check: PASS (23 files)
forbidden path check: PASS (21 absent)
file type check: PASS (regular files/directories only)
```

A second read-only Python scan checked generated UTF-8 files for five signature
classes: private-key headers, AWS access-key identifiers, GitHub tokens,
OpenAI-style keys, and quoted assignments to password/secret/API-key names.
Pre-existing orchestration markers `JOB.md` and `.factory-workspace` were not
treated as generated material and were not read by this scan. Observed exit
status: `0`; output:

```text
credential signature scan: PASS (5 pattern classes, no matches)
```

A final strict-JSON check compared `MANIFEST.yaml` with the authoritative object
and checked the provenance snapshot hash, project/source identifiers, source
commit, and no-copy license flag. Observed exit status: `0`; output:

```text
immutable metadata binding check: PASS
```

These deterministic structure checks passed. The artifact remains partial
because its Java implementation and tests could not be compiled or executed.
