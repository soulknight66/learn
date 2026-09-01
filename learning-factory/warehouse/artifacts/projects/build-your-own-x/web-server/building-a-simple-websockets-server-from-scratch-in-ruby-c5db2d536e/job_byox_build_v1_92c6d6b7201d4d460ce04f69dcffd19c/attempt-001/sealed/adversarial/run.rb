# frozen_string_literal: true

$LOAD_PATH.unshift(File.expand_path("../reference/lib", __dir__))
require "tiny_ws"

checks = 0

def assert(condition, message)
  raise message unless condition
end

lengths = [0, 1, 2, 124, 125, 126, 127, 1024]
lengths.each_with_index do |length, index|
  payload = (0...length).map { |i| (i * 31 + index) & 0xFF }.pack("C*")
  wire = TinyWS::Frame.encode(
    opcode: index.even? ? 1 : 2,
    payload: payload,
    mask: true,
    masking_key: [index, index + 1, index + 2, index + 3].pack("C*")
  )
  cut_points = [0, 1, 2, wire.bytesize / 2, wire.bytesize - 1, wire.bytesize].uniq
  cut_points.each do |cut|
    decoder = TinyWS::FrameDecoder.new(require_mask: true,
                                       max_frame_bytes: 2048)
    decoder.feed(wire.byteslice(0, cut) || "".b)
    first = decoder.next_frame
    if cut < wire.bytesize
      assert(first.nil?, "decoded incomplete frame at #{cut}/#{wire.bytesize}")
      decoder.feed(wire.byteslice(cut, wire.bytesize - cut))
      first = decoder.next_frame
    end
    assert(first.payload == payload, "payload mismatch at length #{length}")
    assert(decoder.next_frame.nil?, "decoder emitted an extra frame")
    checks += 1
  end
end

invalid = [
  [0xC1, 0x80],                         # RSV1 without extension
  [0x81, 0x00],                         # unmasked client frame
  [0x8B, 0x80],                         # reserved control opcode
  [0x09, 0x80],                         # fragmented ping
  [0x82, 0xFE, 0x00, 0x7D],             # noncanonical 16-bit length
  [0x82, 0xFF, 0x80, 0, 0, 0, 0, 0, 0, 0] # forbidden high bit
]
invalid.each do |header|
  decoder = TinyWS::FrameDecoder.new(require_mask: true,
                                     max_frame_bytes: 4096)
  decoder.feed(header.pack("C*") + "mask".b)
  begin
    decoder.next_frame
    raise "invalid header was accepted: #{header.inspect}"
  rescue TinyWS::ProtocolError
    checks += 1
  end
end

puts "PASS #{checks} deterministic adversarial checks"

