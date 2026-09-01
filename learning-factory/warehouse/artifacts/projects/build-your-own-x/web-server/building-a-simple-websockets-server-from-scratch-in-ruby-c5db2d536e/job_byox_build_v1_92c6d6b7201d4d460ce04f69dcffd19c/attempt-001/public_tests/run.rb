# frozen_string_literal: true

require "stringio"
require_relative "test_harness"

library = ENV["TINY_WS_LIB"] || File.expand_path("../starter/lib", __dir__)
$LOAD_PATH.unshift(File.expand_path(library))
require "tiny_ws"

PublicTest.test("handshake accept derivation") do
  actual = TinyWS::Handshake.accept_for("dGhlIHNhbXBsZSBub25jZQ==")
  PublicTest.assert_equal("s3pPLMBiTxaQ9kYGzzhZRbK+xOo=", actual)
end

PublicTest.test("strict valid upgrade") do
  raw = "GET /chat HTTP/1.1\r\n" \
        "Host: example.test\r\n" \
        "Upgrade: WebSocket\r\n" \
        "Connection: keep-alive, Upgrade\r\n" \
        "Sec-WebSocket-Version: 13\r\n" \
        "Sec-WebSocket-Key: AAECAwQFBgcICQoLDA0ODw==\r\n\r\n"
  request = TinyWS::HTTPUpgrade.parse(raw.b)
  PublicTest.assert_equal(request, TinyWS::HTTPUpgrade.validate!(request))
end

PublicTest.test("invalid key is rejected") do
  raw = "GET / HTTP/1.1\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n" \
        "Sec-WebSocket-Version: 13\r\nSec-WebSocket-Key: c2hvcnQ=\r\n\r\n"
  request = TinyWS::HTTPUpgrade.parse(raw.b)
  PublicTest.assert_raises(TinyWS::HandshakeError) do
    TinyWS::HTTPUpgrade.validate!(request)
  end
end

PublicTest.test("small server frame encoding") do
  encoded = TinyWS::Frame.encode(opcode: 1, payload: "Hi".b)
  PublicTest.assert_equal([0x81, 0x02, 0x48, 0x69].pack("C*"), encoded)
end

PublicTest.test("masked frame round trip") do
  key = [0x37, 0xFA, 0x21, 0x3D].pack("C*")
  encoded = TinyWS::Frame.encode(
    opcode: 1, payload: "Hello".b, mask: true, masking_key: key
  )
  decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 128)
  decoder.feed(encoded)
  frame = decoder.next_frame
  PublicTest.assert_equal(true, frame.fin)
  PublicTest.assert_equal(1, frame.opcode)
  PublicTest.assert_equal("Hello".b, frame.payload)
end

PublicTest.test("decoder waits for split input") do
  encoded = TinyWS::Frame.encode(
    opcode: 2, payload: "abcdef".b, mask: true, masking_key: "mask".b
  )
  decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 64)
  encoded.byteslice(0, encoded.bytesize - 1).each_byte.with_index do |byte, index|
    decoder.feed(byte.chr)
    frame = decoder.next_frame
    PublicTest.assert(frame.nil?, "decoded too early at byte #{index}")
  end
  decoder.feed(encoded.byteslice(-1, 1))
  frame = decoder.next_frame
  PublicTest.assert_equal("abcdef".b, frame.payload)
end

PublicTest.test("oversized advertised frame is rejected early") do
  decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 8)
  header = [0x82, 0xFE, 0x00, 0x09].pack("C*")
  decoder.feed(header)
  error = PublicTest.assert_raises(TinyWS::LimitError) { decoder.next_frame }
  PublicTest.assert_equal(1009, error.close_code)
end

PublicTest.test("fragmented control frame is rejected") do
  decoder = TinyWS::FrameDecoder.new(require_mask: true, max_frame_bytes: 128)
  decoder.feed([0x09, 0x80].pack("C*"))
  error = PublicTest.assert_raises(TinyWS::ProtocolError) { decoder.next_frame }
  PublicTest.assert_equal(1002, error.close_code)
end

PublicTest.run!
