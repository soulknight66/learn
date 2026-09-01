# Generation validation record

Artifact status: **GENERATED + PARTIAL**  
Independent validation: **REQUIRED**  
Productionized: **no**

This record contains only commands actually executed in the allocated workspace
on 2026-08-31. No native test, fuzz, benchmark, transfer, or production label is
claimed.

## Toolchain discovery

Commands:

```bash
command -v fpc
command -v ppcx64
python3 --version
```

Observed:

```text
command -v fpc: exit 1, no stdout
command -v ppcx64: exit 1, no stdout
Python 3.6.8
```

Free Pascal is unavailable on `PATH`.

## Native build attempts

Command:

```bash
make -C starter
```

Observed result: exit 2. Relevant output:

```text
mkdir -p bin units
fpc -Mobjfpc -Sh -O1 -g -gl -Fusrc -FUunits -FEbin src/mica.pas
make: fpc: Command not found
make: *** [Makefile:10: bin/mica] Error 127
```

Command:

```bash
make -C sealed/reference
```

Observed result: exit 2. Relevant output:

```text
mkdir -p bin units
fpc -Mobjfpc -Sh -O2 -g -gl -Fusrc -FUunits -FEbin src/mica.pas
make: fpc: Command not found
make: *** [Makefile:10: bin/mica] Error 127
```

Command:

```bash
environment/check.sh
```

Observed result: exit 2 with stderr:

```text
PARTIAL: Pascal compiler 'fpc' is unavailable and MICA_BIN is not executable
```

No Mica executable was produced. Consequently neither
`public_tests/run_tests.py` nor `sealed/reference_tests/run_reference_tests.py`
was executed against a native candidate; doing so without an executable would
only test setup failure. This is the blocker responsible for `PARTIAL`.

## Checks supported by this host

Shell syntax command:

```bash
bash -n environment/check.sh
```

Observed: exit 0 (`bash syntax: PASS` in the combined check log).

Python syntax command (parses source without creating bytecode caches):

```bash
python3 -c "import ast; paths=['public_tests/run_tests.py','sealed/reference_tests/run_reference_tests.py','sealed/benchmarks/benchmark_driver.py']; [ast.parse(open(p, encoding='utf-8').read(), filename=p) for p in paths]; print('python syntax: PASS (3 files)')"
```

Observed: exit 0, `python syntax: PASS (3 files)`.

Strict JSON parse command:

```bash
python3 -c "import json; paths=['MANIFEST.yaml','PROVENANCE.json','sealed/adversarial/cases.json']; [json.load(open(p, encoding='utf-8')) for p in paths]; print('strict JSON parse: PASS (3 files)')"
```

Observed: exit 0, `strict JSON parse: PASS (3 files)`.

`MANIFEST.yaml` was also compared as a parsed object against the authoritative
nine-field object: exit 0, `manifest exact object: PASS`.

Metadata file hashes observed with `sha256sum MANIFEST.yaml PROVENANCE.json`:

```text
ae785b7b18135dfce203f576beb7db5c012920046b52d851b33fa8a5b50932cc  MANIFEST.yaml
8dec1885294f3e1e88f20ce3eaaec0d6c3cf80e4831e5cb702b07bba4db4a7e4  PROVENANCE.json
```

These are file-byte hashes for reproducibility; the immutable catalog snapshot
identifier inside the files remains the required
`39c21180cbc5ede2240b48eb399513125810e87c29d484501064179bd9c5b2aa`.

## Final structure and disclosure checks

After all files were written, a deterministic path check compared every entry in
the authoritative required and forbidden lists. Observed result: all required
paths are regular files; none of the forbidden paths exists.

`find` was used to check for symbolic links and non-file/non-directory nodes.
Observed result: none found.

A credential-pattern scan of generated regular files checked for PEM private-key
headers, AWS access-key shapes, common GitHub/OpenAI token shapes, and assignments
to password/API-key/secret fields. Observed result: no matches. Catalog metadata
such as repository URLs is provenance, not a credential.

## Required independent follow-up

An independent validator with Free Pascal must compile both starter and sealed
reference trees, run public and sealed suites with bounded subprocess timeouts,
and retain compiler/test logs. Static authorship and a successful generator exit
must not be promoted to `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED` evidence.
