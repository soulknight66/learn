# frozen_string_literal: true

require "securerandom"

module TinyWS
  class Frame
    VALID_OPCODES = [0x0, 0x1, 0x2, 0x8, 0x9, 0xA].freeze
    MAX_LENGTH = 0x7FFF_FFFF_FFFF_FFFF

    attr_reader :fin, :opcode, :payload

    def initialize(fin:, opcode:, payload:)
      @fin = fin
      @opcode = opcode
      @payload = payload.b.freeze
    end

    def self.encode(opcode:, payload:, fin: true, mask: false, masking_key: nil)
      raise TypeError, "payload must be a String" unless payload.is_a?(String)
      raise ProtocolError, "invalid opcode" unless VALID_OPCODES.include?(opcode)
      data = payload.b
      length = data.bytesize
      raise LimitError, "frame is too large" if length > MAX_LENGTH
      if opcode >= 0x8 && (!fin || length > 125)
        raise ProtocolError, "invalid control frame"
      end

      first = (fin ? 0x80 : 0) | opcode
      mask_bit = mask ? 0x80 : 0
      header = [first].pack("C")
      if length <= 125
        header << [mask_bit | length].pack("C")
      elsif length <= 0xFFFF
        header << [mask_bit | 126, length].pack("Cn")
      else
        header << [mask_bit | 127, length >> 32, length & 0xFFFF_FFFF].pack("CNN")
      end

      return header << data unless mask
      key = masking_key || SecureRandom.random_bytes(4)
      raise ArgumentError, "masking key must contain four bytes" unless key.is_a?(String) && key.bytesize == 4
      header << key.b << apply_mask(data, key)
    end

    def self.apply_mask(data, key)
      output = String.new(capacity: data.bytesize, encoding: Encoding::BINARY)
      data.each_byte.with_index { |byte, i| output << (byte ^ key.getbyte(i & 3)) }
      output
    end
    private_class_method :apply_mask
  end

  class FrameDecoder
    VALID_OPCODES = Frame::VALID_OPCODES

    def initialize(require_mask:, max_frame_bytes:)
      raise ArgumentError, "max_frame_bytes must be nonnegative" if max_frame_bytes.to_i < 0
      @require_mask = require_mask
      @max_frame_bytes = max_frame_bytes.to_i
      @buffer = "".b
    end

    def feed(bytes)
      raise TypeError, "bytes must be a String" unless bytes.is_a?(String)
      @buffer << bytes.b
      self
    end

    def next_frame
      return nil if @buffer.bytesize < 2
      first = @buffer.getbyte(0)
      second = @buffer.getbyte(1)
      fin = (first & 0x80) != 0
      raise ProtocolError, "RSV bits require a negotiated extension" unless (first & 0x70).zero?

      opcode = first & 0x0F
      raise ProtocolError, "reserved opcode" unless VALID_OPCODES.include?(opcode)
      control = opcode >= 0x8
      length_code = second & 0x7F
      masked = (second & 0x80) != 0
      raise ProtocolError, "client frames must be masked" if @require_mask && !masked
      if control && (!fin || length_code > 125)
        raise ProtocolError, "invalid control frame"
      end

      offset = 2
      noncanonical = false
      case length_code
      when 126
        return nil if @buffer.bytesize < offset + 2
        length = @buffer.byteslice(offset, 2).unpack("n").first
        noncanonical = length < 126
        offset += 2
      when 127
        return nil if @buffer.bytesize < offset + 8
        high, low = @buffer.byteslice(offset, 8).unpack("NN")
        raise ProtocolError, "frame length high bit is set" unless (high & 0x8000_0000).zero?
        length = (high << 32) | low
        noncanonical = length <= 0xFFFF
        offset += 8
      else
        length = length_code
      end

      raise LimitError, "frame exceeds configured limit" if length > @max_frame_bytes
      raise ProtocolError, "noncanonical frame length" if noncanonical
      raise ProtocolError, "control frame exceeds 125 bytes" if control && length > 125

      if masked
        return nil if @buffer.bytesize < offset + 4
        key = @buffer.byteslice(offset, 4)
        offset += 4
      end
      return nil if @buffer.bytesize < offset + length

      payload = @buffer.byteslice(offset, length) || "".b
      consumed = offset + length
      @buffer = @buffer.byteslice(consumed, @buffer.bytesize - consumed) || "".b
      payload = apply_mask(payload, key) if masked
      Frame.new(fin: fin, opcode: opcode, payload: payload)
    end

    private

    def apply_mask(data, key)
      output = String.new(capacity: data.bytesize, encoding: Encoding::BINARY)
      data.each_byte.with_index { |byte, i| output << (byte ^ key.getbyte(i & 3)) }
      output
    end
  end
end
