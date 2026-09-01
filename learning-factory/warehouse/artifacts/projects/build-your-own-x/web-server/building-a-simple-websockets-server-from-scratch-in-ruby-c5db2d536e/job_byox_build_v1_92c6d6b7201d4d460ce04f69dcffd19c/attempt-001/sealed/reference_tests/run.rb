# frozen_string_literal: true

require "socket"
require "stringio"
require "timeout"
require_relative "test_harness"
require "tiny_ws"

module Helpers
  module_function

  def valid_request(path = "/socket")
    "GET #{path} HTTP/1.1\r\n" \
      "Host: 127.0.0.1\r\n" \
      "Upgrade: websocket\r\n" \
      "Connection: keep-alive, Upgrade\r\n" \
      "Sec-WebSocket-Version: 13\r\n" \
      "Sec-WebSocket-Key: AAECAwQFBgcICQoLDA0ODw==\r\n\r\n".b
  end

  def masked(opcode, payload, fin = true, key = "mask".b)
    TinyWS::Frame.encode(opcode: opcode, payload: payload.b, fin: fin,
                         mask: true, masking_key: key)
  end

  def read_frame(io, initial = "".b, timeout = 1.0)
    decoder = TinyWS::FrameDecoder.new(require_mask: false,
                                       max_frame_bytes: 1_048_576)
    decoder.feed(initial) unless initial.empty?
    deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + timeout
    loop do
      frame = decoder.next_frame
      return frame if frame
      remaining = deadline - Process.clock_gettime(Process::CLOCK_MONOTONIC)
      raise SealedTest::Failure, "timed out waiting for frame" if remaining <= 0
      raise SealedTest::Failure, "socket did not become readable" unless IO.select([io], nil, nil, remaining)
      # One byte avoids hiding a following frame in this helper's local decoder.
      decoder.feed(io.readpartial(1))
    end
  end

  def read_http(io, timeout = 1.0)
    bytes = "".b
    deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + timeout
    until (boundary = bytes.index("\r\n\r\n".b))
      remaining = deadline - Process.clock_gettime(Process::CLOCK_MONOTONIC)
      raise SealedTest::Failure, "timed out waiting for HTTP response" if remaining <= 0
      raise SealedTest::Failure, "socket did not become readable" unless IO.select([io], nil, nil, remaining)
      bytes << io.readpartial(4096)
    end
    end_at = boundary + 4
    [bytes.byteslice(0, end_at), bytes.byteslice(end_at, bytes.bytesize - end_at) || "".b]
  end

  def close_pair(left, right, thread = nil)
    [left, right].each do |io|
      begin
        io.close if io && !io.closed?
      rescue IOError
        nil
      end
    end
    if thread
      thread.join(0.5)
      thread.kill if thread.alive?
      thread.join
    end
  end
end

SealedTest.test("known handshake derivation") do
  SealedTest.assert_equal(
    "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=",
    TinyWS::Handshake.accept_for("dGhlIHNhbXBsZSBub25jZQ==")
  )
end

SealedTest.test("strict upgrade accepts tokens case-insensitively") do
  request = TinyWS::HTTPUpgrade.parse(Helpers.valid_request)
  SealedTest.assert_equal(request, TinyWS::HTTPUpgrade.validate!(request))
  response = TinyWS::Handshake.response_for(request)
  SealedTest.assert(response.start_with?("HTTP/1.1 101 Switching Protocols\r\n"))
  SealedTest.assert(response.end_with?("\r\n\r\n"))
end

SealedTest.test("bare LF and folded fields are rejected") do
  SealedTest.assert_raises(TinyWS::HandshakeError) do
    TinyWS::HTTPUpgrade.parse("GET / HTTP/1.1\nHost: x\n\n".b)
  end
  folded = Helpers.valid_request.sub("Host: 127.0.0.1\r\n", "Host: x\r\n folded\r\n")
  SealedTest.assert_raises(TinyWS::HandshakeError) do
    TinyWS::HTTPUpgrade.parse(folded)
  end
end

SealedTest.test("duplicate and noncanonical keys are rejected") do
  duplicate = Helpers.valid_request.sub(
    "Sec-WebSocket-Key: AAECAwQFBgcICQoLDA0ODw==\r\n",
    "Sec-WebSocket-Key: AAECAwQFBgcICQoLDA0ODw==\r\n" \
    "Sec-WebSocket-Key: AAECAwQFBgcICQoLDA0ODw==\r\n"
  )
  request = TinyWS::HTTPUpgrade.parse(duplicate)
  SealedTest.assert_raises(TinyWS::HandshakeError) do
    TinyWS::HTTPUpgrade.validate!(request)
  end

  bad = Helpers.valid_request.sub("AAECAwQFBgcICQoLDA0ODw==", "c2hvcnQ=")
  request = TinyWS::HTTPUpgrade.parse(bad)
  SealedTest.assert_raises(TinyWS::HandshakeError) do
    TinyWS::HTTPUpgrade.validate!(request)
  end
end

SealedTest.test("HTTP reader preserves read-ahead bytes") do
  left, right = Socket.pair(:UNIX, :STREAM, 0)
  frame = Helpers.masked(1, "next")
  writer = Thread.new { right.write(Helpers.valid_request + frame) }
  request = TinyWS::HTTPUpgrade.read(left, max_bytes: 4096, timeout: 1.0)
  SealedTest.assert_equal(frame, request.take_remainder)
ensure
  Helpers.close_pair(left, right, writer)
end

SealedTest.test("frame lengths use all three canonical forms") do
  [[125, 125, 2], [126, 126, 4], [65_536, 127, 10]].each do |size, marker, header_size|
    encoded = TinyWS::Frame.encode(opcode: 2, payload: "x".b * size)
    SealedTest.assert_equal(marker, encoded.getbyte(1))
    SealedTest.assert_equal(header_size + size, encoded.bytesize)
    decoder = TinyWS::FrameDecoder.new(require_mask: false,
                                       max_frame_bytes: 70_000)
    decoder.feed(encoded)
    SealedTest.assert_equal(size, decoder.next_frame.payload.bytesize)
  end
end

SealedTest.test("decoder handles bytewise and consecutive frames") do
  first = Helpers.masked(1, "alpha", true, "abcd")
  second = Helpers.masked(2, "beta", true, "efgh")
  decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 100)
  (first + second).each_byte do |byte|
    decoder.feed(byte.chr)
    break if decoder.next_frame
  end
  # Re-run deterministically to assert both frames without consuming in probes.
  decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 100)
  decoder.feed(first + second)
  SealedTest.assert_equal("alpha", decoder.next_frame.payload)
  SealedTest.assert_equal("beta", decoder.next_frame.payload)
  SealedTest.assert_equal(nil, decoder.next_frame)
end

SealedTest.test("decoder rejects RSV, missing mask, and reserved opcode") do
  cases = [
    [0xC1, 0x80],
    [0x81, 0x00],
    [0x83, 0x80]
  ]
  cases.each do |header|
    decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 100)
    decoder.feed(header.pack("C*") + "mask")
    SealedTest.assert_raises(TinyWS::ProtocolError) { decoder.next_frame }
  end
end

SealedTest.test("decoder rejects noncanonical and oversized lengths early") do
  decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 200)
  decoder.feed([0x82, 0xFE, 0x00, 0x7D].pack("C*"))
  SealedTest.assert_raises(TinyWS::ProtocolError) { decoder.next_frame }

  decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 8)
  decoder.feed([0x82, 0xFE, 0x00, 0x09].pack("C*"))
  error = SealedTest.assert_raises(TinyWS::LimitError) { decoder.next_frame }
  SealedTest.assert_equal(1009, error.close_code)

  decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 100)
  decoder.feed([0x82, 0xFF, 0x80, 0, 0, 0, 0, 0, 0, 0].pack("C*"))
  SealedTest.assert_raises(TinyWS::ProtocolError) { decoder.next_frame }
end

SealedTest.test("control frame constraints are enforced") do
  decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 200)
  decoder.feed([0x09, 0x80].pack("C*"))
  SealedTest.assert_raises(TinyWS::ProtocolError) { decoder.next_frame }

  SealedTest.assert_raises(TinyWS::ProtocolError) do
    TinyWS::Frame.encode(opcode: 9, payload: "x" * 126)
  end
end

SealedTest.test("fragmentation permits ping and echoes complete message") do
  server_io, client_io = Socket.pair(:UNIX, :STREAM, 0)
  delivered = []
  worker = Thread.new do
    TinyWS::Connection.new(
      server_io, max_frame_bytes: 128, max_message_bytes: 256,
      read_timeout: 1.0
    ).run do |type, payload|
      delivered << [type, payload]
      payload.upcase
    end
  end
  client_io.write(
    Helpers.masked(1, "hel", false, "key1") +
    Helpers.masked(9, "?", true, "key2") +
    Helpers.masked(0, "lo", true, "key3")
  )
  first = Helpers.read_frame(client_io)
  second = Helpers.read_frame(client_io)
  SealedTest.assert_equal([0xA, 0x1], [first.opcode, second.opcode])
  SealedTest.assert_equal("?", first.payload)
  SealedTest.assert_equal("HELLO", second.payload)
  SealedTest.assert_equal([[:text, "hello"]], delivered)
  client_io.write(Helpers.masked(8, [1000].pack("n"), true, "key4"))
  close = Helpers.read_frame(client_io)
  SealedTest.assert_equal(8, close.opcode)
  SealedTest.assert(worker.join(1.0), "connection worker did not finish")
ensure
  Helpers.close_pair(server_io, client_io, worker)
end

SealedTest.test("invalid text closes with 1007") do
  server_io, client_io = Socket.pair(:UNIX, :STREAM, 0)
  worker = Thread.new do
    TinyWS::Connection.new(
      server_io, max_frame_bytes: 128, max_message_bytes: 128,
      read_timeout: 1.0
    ).run { |_type, payload| payload }
  end
  client_io.write(Helpers.masked(1, "\xFF".b))
  close = Helpers.read_frame(client_io)
  SealedTest.assert_equal(8, close.opcode)
  SealedTest.assert_equal(1007, close.payload.unpack("n").first)
  SealedTest.assert(worker.join(1.0), "connection worker did not finish")
ensure
  Helpers.close_pair(server_io, client_io, worker)
end

SealedTest.test("fragmented message bound closes with 1009") do
  server_io, client_io = Socket.pair(:UNIX, :STREAM, 0)
  worker = Thread.new do
    TinyWS::Connection.new(
      server_io, max_frame_bytes: 8, max_message_bytes: 5,
      read_timeout: 1.0
    ).run { |_type, payload| payload }
  end
  client_io.write(Helpers.masked(2, "abcd", false) + Helpers.masked(0, "ef", true))
  close = Helpers.read_frame(client_io)
  SealedTest.assert_equal(1009, close.payload.unpack("n").first)
  SealedTest.assert(worker.join(1.0), "connection worker did not finish")
ensure
  Helpers.close_pair(server_io, client_io, worker)
end

SealedTest.test("invalid close payload sends one protocol close") do
  server_io, client_io = Socket.pair(:UNIX, :STREAM, 0)
  worker = Thread.new do
    TinyWS::Connection.new(
      server_io, max_frame_bytes: 128, max_message_bytes: 128,
      read_timeout: 1.0
    ).run
  end
  client_io.write(Helpers.masked(8, "x"))
  close = Helpers.read_frame(client_io)
  SealedTest.assert_equal(1002, close.payload.unpack("n").first)
  SealedTest.assert(worker.join(1.0), "connection worker did not finish")
ensure
  Helpers.close_pair(server_io, client_io, worker)
end

SealedTest.test("loopback server upgrades read-ahead frame and shuts down") do
  server = TinyWS::Server.new(
    host: "127.0.0.1", port: 0, max_clients: 2,
    max_header_bytes: 4096, max_frame_bytes: 128,
    max_message_bytes: 128, handshake_timeout: 1.0, read_timeout: 1.0
  ) { |_type, payload| "echo:#{payload}" }
  begin
    server.start
  rescue Errno::EPERM, Errno::EACCES => error
    SealedTest.skip("loopback TCP unavailable: #{error.class}: #{error.message}")
  end
  client = TCPSocket.new("127.0.0.1", server.port)
  client.write(Helpers.valid_request + Helpers.masked(1, "hi"))
  response, remainder = Helpers.read_http(client)
  SealedTest.assert(response.start_with?("HTTP/1.1 101"))
  echoed = Helpers.read_frame(client, remainder)
  SealedTest.assert_equal("echo:hi", echoed.payload)
  client.write(Helpers.masked(8, [1000].pack("n")))
  SealedTest.assert_equal(8, Helpers.read_frame(client).opcode)
ensure
  client.close if client && !client.closed?
  if server
    started = Process.clock_gettime(Process::CLOCK_MONOTONIC)
    server.stop(join_timeout: 1.0)
    elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started
    SealedTest.assert(elapsed < 1.5, "server shutdown exceeded bound")
  end
end

SealedTest.run!
