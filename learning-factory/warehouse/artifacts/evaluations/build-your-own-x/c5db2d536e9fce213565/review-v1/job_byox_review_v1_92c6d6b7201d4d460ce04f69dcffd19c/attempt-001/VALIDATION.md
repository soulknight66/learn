# Independent validation record

Review date: 2026-08-31. Commands ran from `CANDIDATE/` unless shown otherwise. Every potentially blocking command used a 5–20 second bound. Repeated `/usr/bin/id` warnings about unmapped sandbox IDs were launcher noise and did not alter command exit status.

## Runtime and compilation

```bash
ruby --version
```

Exit 0: `ruby 2.5.9p229 (2021-04-05 revision 67939) [x86_64-linux]`.

```bash
ruby -e 'require "minitest/autorun"; puts "minitest available"'
```

Exit 1: `LoadError: cannot load such file -- minitest/autorun`. The candidate's dependency-free harness was therefore used.

```bash
ruby -e 'files=(Dir["{starter,public_tests,sealed}/**/*.rb"] + ["starter/bin/tiny_ws", "sealed/reference/bin/tiny_ws"]).uniq.sort; files.each { |file| RubyVM::InstructionSequence.compile_file(file) }; puts "Ruby syntax: #{files.length} files compiled"'
```

Exit 0: `Ruby syntax: 22 files compiled`.

## Supplied behavior checks, independently rerun

```bash
timeout 15s ruby -Istarter/lib public_tests/run.rb
```

Exit 1: all eight cases failed with the scaffold's documented `NotImplementedError`; summary `0/8 public checks passed`.

```bash
timeout 15s env TINY_WS_LIB=sealed/reference/lib ruby public_tests/run.rb
```

Exit 0: eight PASS lines; summary `8/8 public checks passed`.

```bash
timeout 20s ruby -Isealed/reference/lib sealed/reference_tests/run.rb
```

Exit 0: `14 passed, 1 skipped, 0 failed`. The skipped case was `loopback server upgrades read-ahead frame and shuts down`, with `Errno::EPERM` on loopback socket creation.

```bash
timeout 15s ruby sealed/adversarial/run.rb
```

Exit 0: `PASS 54 deterministic adversarial checks`. This enumerated self-runner was not treated as fuzzing or independent conformance evidence.

```bash
timeout 15s ruby sealed/validate_pack.rb
```

Exit 0: `PASS structure, forbidden paths, metadata status, regular-file policy, and credential scan`. Its coverage limitations are recorded below.

```bash
timeout 5s ruby sealed/reference/bin/tiny_ws --help
```

Exit 0; help exposed host, port, four byte/client limits, handshake timeout, and read timeout.

## Reviewer-authored protocol checks

The following independent harness used known/manual wire bytes rather than the candidate encoder to construct its decode and connection-error inputs:

```bash
timeout 10s ruby -Isealed/reference/lib -rsocket -e '
require "tiny_ws"
def check(name)
  raise "FAIL #{name}" unless yield
  puts "PASS #{name}"
end
wire = ["818537fa213d7f9f4d5158"].pack("H*")
decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 32)
decoder.feed(wire)
frame = decoder.next_frame
check("independent RFC masked Hello decode") {
  frame.fin && frame.opcode == 1 && frame.payload == "Hello".b && decoder.next_frame.nil?
}
encoded = TinyWS::Frame.encode(opcode: 2, payload: "x".b * 126)
check("independent 16-bit canonical header") {
  encoded.byteslice(0, 4) == [0x82, 0x7e, 0x00, 0x7e].pack("C*") && encoded.bytesize == 130
}
raw = ("GET / HTTP/1.1\r\nHost: example\r\nX-Test: one\r\nX-Test: two\r\n" \
       "Upgrade: websocket\r\nConnection: keep-alive, Upgrade\r\n" \
       "Sec-WebSocket-Version: 13\r\n" \
       "Sec-WebSocket-Key: AAECAwQFBgcICQoLDA0ODw==\r\n\r\nTAIL").b
request = TinyWS::HTTPUpgrade.parse(raw)
check("duplicate ordinary headers and read-ahead") {
  TinyWS::HTTPUpgrade.validate!(request).equal?(request) &&
    request.header_values("x-test") == ["one", "two"] &&
    request.take_remainder == "TAIL".b && request.take_remainder.empty?
}
server_io, client_io = Socket.pair(:UNIX, :STREAM, 0)
worker = Thread.new {
  TinyWS::Connection.new(server_io, max_frame_bytes: 16,
                         max_message_bytes: 16, read_timeout: 0.5).run
}
client_io.write([0x80, 0x81, 0x6d, 0x61, 0x73, 0x6b, 0x15].pack("C*"))
close = IO.select([client_io], nil, nil, 1.0) && client_io.readpartial(4)
check("unexpected continuation closes 1002") {
  close == [0x88, 0x02, 0x03, 0xea].pack("C*") && worker.join(1.0)
}
server_io.close unless server_io.closed?
client_io.close unless client_io.closed?
left, right = Socket.pair(:UNIX, :STREAM, 0)
started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
begin
  TinyWS::HTTPUpgrade.read(left, max_bytes: 64, timeout: 0.05)
  timed_out = false
rescue TinyWS::HandshakeError => error
  elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started
  timed_out = error.message.include?("timed out") && elapsed < 0.5
ensure
  left.close unless left.closed?
  right.close unless right.closed?
end
check("bounded silent-handshake timeout") { timed_out }
puts "5/5 independent protocol checks passed"
'
```

Exit 0. All five named cases passed.

## Independent correctness and learner-interface probes

```bash
timeout 5s ruby -Isealed/reference/lib -rsocket -e '
require "tiny_ws"
server_io, client_io = Socket.pair(:UNIX, :STREAM, 0)
result = :unset
worker = Thread.new do
  begin
    TinyWS::Connection.new(server_io, max_frame_bytes: 16,
                           max_message_bytes: 16, read_timeout: 0.5).run do
      raise TinyWS::ProtocolError.new("application failure", 1008)
    end
    result = :returned
  rescue => error
    result = error.class
  end
end
client_io.write([0x81, 0x81, 0x6d, 0x61, 0x73, 0x6b, 0x15].pack("C*"))
wire = IO.select([client_io], nil, nil, 1.0) && client_io.readpartial(4)
worker.join(1.0)
puts "wire=#{wire.unpack("H*").first}"
puts "worker_result=#{result}"
server_io.close unless server_io.closed?
client_io.close unless client_io.closed?
'
```

Exit 0: `wire=880203f0`, `worker_result=returned`. Thus an application-raised protocol exception was suppressed and emitted as peer-policy close 1008.

```bash
timeout 5s ruby -Isealed/reference/lib -e 'require "tiny_ws"; server=TinyWS::Server.new; seen=nil; Signal.trap("USR1") { begin; server.stop; seen="no error"; rescue => e; seen="#{e.class}: #{e.message}"; end }; Process.kill("USR1", Process.pid); sleep 0.05 until seen; puts seen'
```

Exit 0 with observed result `ThreadError: can't be called from trap context`. This exercises the direct-stop trap pattern supplied in the starter against the synchronized reference stop.

```bash
ruby starter/bin/tiny_ws --help
ruby sealed/reference/bin/tiny_ws --help
```

Both exited 0. The starter omitted `--handshake-timeout` and `--read-timeout`; the reference included them.

```bash
ruby -e 'text=File.binread("public_tests/run.rb"); puts "Connection references=#{text.scan(/TinyWS::Connection/).length}"; puts "Server references=#{text.scan(/TinyWS::Server/).length}"; puts "test cases=#{text.scan(/PublicTest\.test/).length}"'
```

Exit 0: `Connection references=0`, `Server references=0`, `test cases=8`.

```bash
ruby -e 'text=File.binread("sealed/validate_pack.rb"); required=text[/REQUIRED = %w\[(.*?)\]\.freeze/m,1].to_s.split; essential=%w[starter/lib/tiny_ws.rb starter/bin/tiny_ws public_tests/run.rb public_tests/test_harness.rb sealed/reference/lib/tiny_ws.rb sealed/reference/bin/tiny_ws sealed/reference_tests/run.rb sealed/adversarial/run.rb]; essential.each { |path| puts "#{path}: required=#{required.include?(path)}" }'
```

Exit 0: all eight essential paths printed `required=false`.

## Metadata, packaging, and disclosure

```bash
ruby -rjson -rdigest -e 'm=JSON.parse(File.binread("CANDIDATE/MANIFEST.yaml")); p=JSON.parse(File.binread("CANDIDATE/PROVENANCE.json")); puts "manifest_project=#{m.fetch("project_id")}"; puts "provenance_project=#{p.dig("project","project_id")}"; puts "manifest_source=#{m.fetch("source_id")}@#{m.fetch("source_commit")}"; puts "provenance_source=#{p.dig("source","source_id")}@#{p.dig("source","commit_hash")}"; puts "manifest_provenance_sha256=#{m.fetch("provenance_sha256")}"; puts "embedded_snapshot_sha256=#{p.fetch("snapshot_sha256")}"; puts "provenance_file_sha256=#{Digest::SHA256.file("CANDIDATE/PROVENANCE.json").hexdigest}"; puts "labels=#{m.fetch("validation_labels").join(",")}"'
```

Exit 0. Project/source IDs and commits matched. Observed hashes:

- manifest `provenance_sha256`: `aa3c412b3df6335355c1c77e7d9226a99d11df1604e54a4369e515acd2b99773`
- embedded `snapshot_sha256`: the same `aa3c...`
- actual `PROVENANCE.json` SHA-256: `aeab6f1ca97e81772410751a4cf2f1733410bbc8f4ecb021b33969d534f575b3`
- deterministic 47-file content/path inventory digest: `0dec63be73806b4aec889887d433ae42f55e8cacb38536499f4c854d8d78d329`

The inventory digest was computed without modifying the candidate:

```bash
ruby -rdigest -e 'rows=Dir.glob("CANDIDATE/**/*", File::FNM_DOTMATCH).select { |p| File.file?(p) }.sort.map { |p| "#{Digest::SHA256.file(p).hexdigest}  #{p.sub(%r{\ACANDIDATE/}, "")}" }; puts Digest::SHA256.hexdigest(rows.join("\n")); puts "files=#{rows.length}"'
```

Exit 0: the digest above and `files=47`.

```bash
ruby -e 'paths=Dir.glob("CANDIDATE/**/*", File::FNM_DOTMATCH); files=paths.select { |p| File.file?(p) }; links=paths.select { |p| File.symlink?(p) }; special=paths.reject { |p| File.file?(p) || File.directory?(p) || File.symlink?(p) }; puts "regular_files=#{files.length}"; puts "symlinks=#{links.length}"; puts "special_files=#{special.length}"; puts "world_writable=#{files.count { |p| (File.stat(p).mode & 2) != 0 }}"'
```

Run from the review root, exit 0: `regular_files=47`, `symlinks=0`, `special_files=0`, `world_writable=0`.

```bash
ruby -e 'targets=%w[CANDIDATE/sealed/DESIGN.md CANDIDATE/sealed/reference/lib/tiny_ws.rb CANDIDATE/sealed/reference_tests/run.rb CANDIDATE/sealed/debugging/exercise_01/sealed/ANSWER.md]; targets.each { |p| puts "#{p}: readable=#{File.readable?(p)} mode=%04o" % (File.stat(p).mode & 0777) }'
```

Run from the review root, exit 0: every target printed `readable=true mode=0444`.

```bash
find CANDIDATE -maxdepth 2 -type f \( -iname 'LICENSE' -o -iname 'LICENSE.*' -o -iname 'COPYING' -o -iname 'COPYING.*' \) -print
```

Exit 0 with no output. `LICENSE_BOUNDARY.md` exists, but no explicit generated-artifact license file was found.

```bash
grep -RInE '\b(BUILDS|TESTED|FUZZED|BENCHMARKED|REVIEWED|TRANSFER_VERIFIED|PRODUCTIONIZED)\b' CANDIDATE
```

Exit 0. Every occurrence was a disclaimer or a warning not to promote a label; the manifest contains only `GENERATED` and `PARTIAL`.

## Environment blocker

```bash
timeout 5s ruby -rsocket -e 'server=TCPServer.new("127.0.0.1",0); puts server.addr[1]; server.close'
```

Exit 1: `Errno::EPERM: Operation not permitted - socket(2) for "127.0.0.1" port 0`. Consequently, TCP bind/accept, capacity, and teardown claims remain inconclusive.

The source snapshot and linked article were outside the permitted workspace and network access was unavailable. No source/license comparison, external conformance suite, fuzzer, benchmark, alternate runtime, transfer check, or production trial was performed.
