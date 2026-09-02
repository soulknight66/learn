# Independent reviewer validation

Date: 2026-09-02 (America/Chicago)

Disposition: advisory review evidence only. `CANDIDATE/` was treated as
immutable. Mutation-producing checks ran in `.review-validation/` copies; the
scratch tree was removed after the observations below were recorded. No label
was added to the candidate manifest.

## Tool identities

Every relevant configured tool was invoked by its absolute path.

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
GNU ld (GNU Binutils) 2.43

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-gcc --version
arm-none-eabi-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-readelf --version
GNU readelf (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203

$ /usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm --version
QEMU emulator version 9.1.1

$ /usr/bin/make --version
GNU Make 4.2.1

$ /usr/bin/timeout --version
timeout (GNU coreutils) 8.30
```

The other configured Java, AArch64, Node, Go, NASM, Flex, and Bison roots were
not relevant to this C/ARM challenge and were not used. No required toolchain
was unavailable. `rg` and `git` were not available, so the review used bounded
`find`, `grep`, Python, and direct reads; no repository history was present.

## Submission integrity and metadata

A configured-Python script sorted the 95 relative file paths, then hashed each
path, a NUL separator, and its bytes into one SHA-256 stream. It ran before and
after all candidate reads:

```text
candidate_files=95
candidate_tree_sha256=342ba30e2f586ee34126774af1771890d61c7e0d8d7135f6164c6de61e53a7fd
postcheck_candidate_tree_sha256=342ba30e2f586ee34126774af1771890d61c7e0d8d7135f6164c6de61e53a7fd
```

Strict `json.loads` parsing of `MANIFEST.yaml` and `PROVENANCE.json` checked the
manifest's exact nine keys; exact `GENERATED`/`PARTIAL` labels; required
independent validation; false production status; and matching project, source,
commit, and snapshot identifiers.

```text
metadata_consistency=PASS
manifest_keys=9
provenance_keys=7
```

The immutable source snapshot and upstream repository were not available, so
the declared commit, CC0 evidence, baseline hashes, and `linked_content_copied:
false` assertion remain internally consistent but externally unverified.

Filesystem scans observed 95 regular files, no symlinks, no special files, and
no solution-named directories below `starter`, `public_tests`, or `environment`.
A byte-aware credential-pattern scan considered 72 nonbinary files and found
zero matching files. There are 41 files below paths named `sealed`; an actual
orchestrator-rendered learner view was not available to test their exclusion.

## Isolated staging

The review staged copies before any build:

```sh
mkdir .review-validation
cp -R CANDIDATE/starter .review-validation/starter
cp -R CANDIDATE/sealed/reference .review-validation/reference
cp -R CANDIDATE/public_tests .review-validation/public_tests
cp -R CANDIDATE/public_tests .review-validation/public_tests_ref
cp -R CANDIDATE/sealed/reference_tests .review-validation/reference_tests
```

The first five `make clean ...` attempts each exited 2 before compilation
because the copies inherited the immutable submission's read-only modes (`rm`
or `mkdir` reported permission denied). This was an isolation/setup failure,
not a candidate build result. The reviewer then ran:

```sh
chmod -R u+w .review-validation
```

Only scratch-copy modes changed. The intended checks below were then rerun.

## Clean ARM builds and reproducibility

```sh
/usr/bin/make -C .review-validation/reference clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-

/usr/bin/make -C .review-validation/starter clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-
```

Both commands exited 0 with `-ffreestanding`, `-Wall -Wextra -Werror`, and
`-nostdlib`. No compiler or linker warning was emitted.

```text
e2fbf1dabd0d0eb9df8d89ae2ba65ffc2c8fe1119c66ef90673b2238d5014540  reference/build/kernel.elf
77fe608a4e066189c27f15e686e606bb20ba9efb1e55bca9f801ba850580d103  reference/build/kernel.bin
fb01da0cf9457b8dc372fa52a8abcdf8d9e0e7406cf3c2105c69512591ca8ee4  starter/build/kernel.elf
a5e6978210f45b0fc27c1604276123099f26f15e2857d30a34a7d6a0b50d2f74  starter/build/kernel.bin
```

`cmp -s` returned 0 for all four submitted/rebuilt pairs. All 12 files in each
submitted target build directory had the same names and bytes as its clean
scratch rebuild.

Arm `readelf -h -l` observed an ELF32, little-endian ARM EABI5 executable with
entry `0x10000`, one RX LOAD, one RW LOAD, and an RW/non-executable GNU stack.

```sh
/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-nm \
  -u .review-validation/reference/build/kernel.elf
```

Observed no symbols, exit 0.

The clean sealed host-test executable behaved identically but was not
byte-identical to the submitted one. `strings` found each build's absolute
compilation directory in its debug data; the submitted binary contains the
builder job workspace path.

## Sanitized host execution

The common environment retained ASan and UBSan while disabling only leak
detection, which the candidate records as incompatible with the sandbox:

```sh
/usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C .review-validation/reference_tests clean test \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed `reference_tests: PASS (400 checks)`, exit 0.

The same environment and compiler ran copied public suites with
`KERNEL_SRC=../reference` and the default `KERNEL_SRC=../starter`.

```text
reference: public_tests: PASS, exit 0
starter:   public_tests: 37 check(s) failed, make exit 2
```

The starter result is the documented intentional baseline. Both isolated
exercise sources also passed a C11 `-Wall -Wextra -Werror -pedantic
-fsyntax-only` compile, exit 0.

A reviewer-authored scratch harness added checks absent from the supplied
machine-readable vector file: mismatched current/running scheduler states and
no-mutation rejection, frame-init past-top no-mutation, combined VM permission
denial, unchanged translation output on failure, successful translation to
`UINT32_MAX`, and RAMFS failure/output atomicity.

```text
independent_edges: PASS (28 checks)
```

It used the same GCC, Binutils prefix, ASan/UBSan flags, runtime library path,
and leak-detection setting as the supplied suites. This is a bounded reviewer
check, not a `FUZZED`, `TESTED`, or other manifest label.

## Bounded emulation

```sh
/usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /usr/bin/timeout 10s \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm \
  -M versatilepb -cpu arm926 -m 128M -nographic -monitor none \
  -semihosting-config enable=on,target=native \
  -kernel .review-validation/reference/build/kernel.elf
```

Observed exit 0 and, in order:

```text
LF-KERNEL boot
mmu: on
vm: ok
ramfs: ok
tasks: ABABAB
PASS reference
```

A binary capture contained 75 bytes, six `CR LF` pairs, and no bare LF. This
independently checks newline translation as well as marker text.

The same invocation with a 2-second bound and the scratch starter ELF emitted
no kernel marker; timeout terminated QEMU and returned 124. This matches the
documented UART/MMU stub baseline.

## Additional evidence audits

The reference passed an independent representation probe, but the probe also
demonstrated noncanonical padding after initialization:

```text
ramfs_size=2240 residual_a5=24 canonical_equal=no
vm_size=192 residual_a5=32 canonical_equal=no
```

This matters because supplied failure-atomicity tests use structure assignment
and `memcmp`; C does not guarantee stable padding values on structure stores.

One diagnostic-only compilation/run of the supplied benchmark harness exited 0:

```text
iterations=100000 elapsed_ns=1389848 checksum=0
```

There was one sample, no threshold, and no controlled host or target study. It
is not evidence for `BENCHMARKED`.

Finally, `adversarial/cases/boundaries.json` parsed successfully and contains six
vectors. Direct comparison with `adversarial/README.md` found that the JSON omits
the advertised stale-PID, corrupt-scheduler, final-physical-byte,
full-capacity-create, and scrub/reuse cases. This factual mismatch drives the
REVISE verdict; the independent harness did not find a corresponding core-code
failure.

## Unvalidated scope

No physical board, upstream checkout, network fetch, actual learner-view
materialization, transfer environment, fuzzer, repeated performance study,
formal proof, security audit, production workload, persistent filesystem,
preemptive interrupt path, userspace isolation, or multicore behavior was
validated.
