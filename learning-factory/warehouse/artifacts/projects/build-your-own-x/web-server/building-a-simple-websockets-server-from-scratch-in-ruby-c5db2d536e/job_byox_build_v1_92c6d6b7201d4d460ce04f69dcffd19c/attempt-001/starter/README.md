# Starter implementation

This directory is the only implementation area learners need to modify. The
files already define the required classes, method signatures, limits, and
command-line surface. Search for `TODO` and work in the order below:

1. `lib/tiny_ws/handshake.rb` and `http_upgrade.rb`
2. `lib/tiny_ws/frame.rb`
3. `lib/tiny_ws/connection.rb`
4. `lib/tiny_ws/server.rb` and `bin/tiny_ws`

Run the public checks from this directory:

```bash
ruby -Ilib ../public_tests/run.rb
```

The initial scaffold intentionally fails behavior checks. Syntax should remain
valid throughout. Keep all network limits finite and do not add gem
dependencies.

