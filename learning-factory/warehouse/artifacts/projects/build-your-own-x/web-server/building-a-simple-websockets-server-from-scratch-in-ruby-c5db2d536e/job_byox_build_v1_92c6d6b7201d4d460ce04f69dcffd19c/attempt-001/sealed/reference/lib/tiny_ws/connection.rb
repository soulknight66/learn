# frozen_string_literal: true

module TinyWS
  class Connection
    READ_SIZE = 4096

    def initialize(io, max_frame_bytes:, max_message_bytes:, read_timeout:,
                   initial_bytes: "".b)
      raise ArgumentError, "max_message_bytes must be nonnegative" if max_message_bytes.to_i < 0
      @io = io
      @decoder = FrameDecoder.new(require_mask: true,
                                  max_frame_bytes: max_frame_bytes)
      @max_message_bytes = max_message_bytes.to_i
      @read_timeout = read_timeout && read_timeout.to_f
      @decoder.feed(initial_bytes) unless initial_bytes.empty?
      @fragment_opcode = nil
      @message = "".b
      @close_sent = false
      @timed_out = false
    end

    def run(&handler)
      handler ||= proc { |_type, _payload| nil }
      loop do
        while (frame = @decoder.next_frame)
          return if process_frame(frame, handler) == :closed
        end

        chunk = read_chunk
        break unless chunk
        @decoder.feed(chunk)
      end
      send_close(1001) if @timed_out
      nil
    rescue ProtocolError => error
      send_close(error.close_code)
      nil
    rescue StandardError
      send_close(1011)
      raise
    end

    private

    def process_frame(frame, handler)
      case frame.opcode
      when 0x0
        raise ProtocolError, "unexpected continuation" unless @fragment_opcode
        append_message(frame.payload)
        complete_message(handler) if frame.fin
      when 0x1, 0x2
        raise ProtocolError, "new data frame during fragmentation" if @fragment_opcode
        if frame.fin
          @fragment_opcode = frame.opcode
          append_message(frame.payload)
          complete_message(handler)
        else
          @fragment_opcode = frame.opcode
          @message = "".b
          append_message(frame.payload)
        end
      when 0x8
        receive_close(frame.payload)
        return :closed
      when 0x9
        write_frame(0xA, frame.payload)
      when 0xA
        # A pong is transport-level information; this API has no observer for it.
      end
      nil
    end

    def append_message(payload)
      if @message.bytesize + payload.bytesize > @max_message_bytes
        raise LimitError, "message exceeds configured limit"
      end
      @message << payload
    end

    def complete_message(handler)
      opcode = @fragment_opcode
      bytes = @message
      if opcode == 0x1
        text = bytes.dup.force_encoding(Encoding::UTF_8)
        raise ProtocolError.new("text message is not UTF-8", 1007) unless text.valid_encoding?
        kind = :text
        delivered = text
      else
        kind = :binary
        delivered = bytes.b
      end

      @fragment_opcode = nil
      @message = "".b
      response = handler.call(kind, delivered)
      return if response.nil?
      raise TypeError, "connection handler must return a String or nil" unless response.is_a?(String)
      raise LimitError, "response exceeds configured limit" if response.bytesize > @max_message_bytes
      if opcode == 0x1
        encoded = response.dup.force_encoding(Encoding::UTF_8)
        raise TypeError, "text response must be valid UTF-8" unless encoded.valid_encoding?
      end
      write_frame(opcode, response.b)
    end

    def receive_close(payload)
      raise ProtocolError, "close payload cannot contain one byte" if payload.bytesize == 1
      unless payload.empty?
        code = payload.byteslice(0, 2).unpack("n").first
        raise ProtocolError, "invalid close code" unless valid_close_code?(code)
        reason = payload.byteslice(2, payload.bytesize - 2).to_s
        utf8_reason = reason.dup.force_encoding(Encoding::UTF_8)
        raise ProtocolError.new("close reason is not UTF-8", 1007) unless utf8_reason.valid_encoding?
      end
      write_close_payload(payload)
    end

    def valid_close_code?(code)
      ((1000..1014).cover?(code) && ![1004, 1005, 1006].include?(code)) ||
        (3000..4999).cover?(code)
    end

    def send_close(code)
      write_close_payload([code].pack("n"))
    rescue IOError, SystemCallError
      nil
    end

    def write_close_payload(payload)
      return if @close_sent
      @close_sent = true
      write_frame(0x8, payload)
    end

    def write_frame(opcode, payload)
      write_all(Frame.encode(opcode: opcode, payload: payload))
    end

    def write_all(bytes)
      offset = 0
      while offset < bytes.bytesize
        written = @io.write(bytes.byteslice(offset, bytes.bytesize - offset))
        raise IOError, "socket write made no progress" unless written && written > 0
        offset += written
      end
    end

    def read_chunk
      if @read_timeout && @read_timeout > 0 && @io.respond_to?(:to_io)
        unless IO.select([@io], nil, nil, @read_timeout)
          @timed_out = true
          return nil
        end
      end
      @io.readpartial(READ_SIZE)
    rescue EOFError
      nil
    rescue IO::WaitReadable
      retry
    end
  end
end
