# frozen_string_literal: true

module TinyWS
  class Frame
    attr_reader :fin, :opcode, :payload

    def initialize(fin:, opcode:, payload:)
      @fin = fin
      @opcode = opcode
      @payload = payload
    end

    def self.encode(opcode:, payload:, fin: true, mask: false, masking_key: nil)
      # TODO: serialize a canonical frame and optionally apply a four-byte mask.
      raise NotImplementedError, "encode a WebSocket frame"
    end
  end

  class FrameDecoder
    VALID_OPCODES = [0x0, 0x1, 0x2, 0x8, 0x9, 0xA].freeze

    def initialize(require_mask:, max_frame_bytes:)
      @require_mask = require_mask
      @max_frame_bytes = max_frame_bytes
      @buffer = "".b
    end

    def feed(bytes)
      raise TypeError, "bytes must be a String" unless bytes.is_a?(String)
      @buffer << bytes.b
      self
    end

    def next_frame
      # TODO: decode one complete frame without consuming partial input.
      raise NotImplementedError, "decode a WebSocket frame"
    end
  end
end

