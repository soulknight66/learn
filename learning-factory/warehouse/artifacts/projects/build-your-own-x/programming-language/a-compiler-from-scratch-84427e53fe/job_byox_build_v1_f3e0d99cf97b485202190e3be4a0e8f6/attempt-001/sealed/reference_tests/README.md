# Sealed reference tests

`test_reference.rb` exercises the independently written implementation beyond the public foothold. Coverage includes every token and opcode family, precedence, malformed syntax, declaration timing, shadowing, branch and loop control flow, signed division/modulo, overflow, hostile bytecode, stack/local failures, and resource limits.

The suite uses the small dependency-free harness in `public_tests/support/harness.rb` because neither minitest nor test-unit is installed on the generation host.

Run:

```sh
ruby -Isealed/reference/lib sealed/reference_tests/test_reference.rb
```

The suite is sealed because its boundary cases reveal much of the solution strategy. Independent validators remain authoritative.
