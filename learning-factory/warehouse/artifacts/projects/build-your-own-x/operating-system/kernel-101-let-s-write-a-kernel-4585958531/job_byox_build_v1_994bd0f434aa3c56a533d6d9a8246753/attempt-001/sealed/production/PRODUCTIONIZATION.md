# Productionization assessment

Status: **not productionized**.

`src/invariant_checks.c` is a prototype audit layer that checks cross-field consistency after API
operations. Its tests demonstrate detection of several corruptions. This is useful hardening work,
but it does not close the gaps below.

## Required before real use

- Replace the page-map model with architecture page tables, TLB invalidation, privilege separation,
  NX enforcement, and verified boot-time memory discovery.
- Define locking and interrupt-disable rules for every shared structure, then test on multiple CPUs.
- Add context switching, saved register frames, kernel/user stacks, syscall entry, and fault handling.
- Replace fixed inline file payloads with a persistent format, buffer cache, journal or copy-on-write
  recovery, permissions, and adversarial pathname handling.
- Protect against counter exhaustion and corrupted public structures; hide representations behind
  opaque APIs.
- Add reproducible cross-compilation, signed release artifacts, SBOM/provenance, emulator tests,
  hardware smoke tests, fuzzing, static analysis, and fault-injection campaigns.
- Specify support, disclosure, rollback, telemetry, and incident-response policies.

The generation host lacked QEMU and GRUB image tools. No boot, security, durability, performance,
or operational-readiness claim is made.
