# frozen_string_literal: true

module TinyWS
  class Connection
    READ_SIZE = 4096

    def initialize(io, max_frame_bytes:, max_message_bytes:, read_timeout:)
      @io = io
      @max_frame_bytes = max_frame_bytes
      @max_message_bytes = max_message_bytes
      @read_timeout = read_timeout
    end

    def run
      # TODO: drive FrameDecoder, fragmentation, control frames, limits, and
      # close handling. Yield |type, payload| once per complete data message.
      raise NotImplementedError, "run the connection state machine"
    end
  end
end

