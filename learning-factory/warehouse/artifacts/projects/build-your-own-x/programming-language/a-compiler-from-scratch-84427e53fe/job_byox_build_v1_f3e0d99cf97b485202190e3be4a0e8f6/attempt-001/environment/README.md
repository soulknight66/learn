# Environment

The artifact targets Ruby 2.5 or newer and uses only the standard library plus its repository-local test harness. It was generated on a host reporting Ruby 2.5.9. No package installation, network service, database, compiler toolchain, or environment variable containing sensitive data is required. The host does not provide the optional `minitest` or `test-unit` gems, so the test files do not depend on either.

Recommended deterministic commands from the repository root:

```sh
ruby --version
ruby -Istarter/lib public_tests/test_public.rb
```

Tests use `StringIO`, so language output does not depend on terminal encoding. Source files should be treated as UTF-8; the defined identifier alphabet is ASCII.
