# frozen_string_literal: true

require "base64"

module TinyWS
  class UpgradeRequest
    attr_reader :method, :target, :version

    def initialize(method, target, version, headers, remainder = "".b)
      @method = method.freeze
      @target = target.freeze
      @version = version.freeze
      @headers = headers
      @remainder = remainder.b
    end

    def header(name)
      values = @headers[name.to_s.downcase]
      return nil unless values
      values.length == 1 ? values.first : values.dup
    end

    def header_values(name)
      values = @headers[name.to_s.downcase]
      values ? values.dup : []
    end

    def take_remainder
      bytes = @remainder
      @remainder = "".b
      bytes
    end
  end

  module HTTPUpgrade
    HEADER_END = "\r\n\r\n".b.freeze
    TOKEN = /\A[!#$%&'*+\-.^_`|~0-9A-Za-z]+\z/.freeze
    module_function

    def read(io, max_bytes: 16_384, timeout: 5.0)
      raise ArgumentError, "max_bytes must be positive" unless max_bytes.to_i > 0
      raise ArgumentError, "timeout must be positive" unless timeout.to_f > 0

      buffer = "".b
      deadline = monotonic_now + timeout.to_f
      loop do
        if (boundary = buffer.index(HEADER_END))
          header_size = boundary + HEADER_END.bytesize
          raise HandshakeError, "HTTP header is too large" if header_size > max_bytes
          block = buffer.byteslice(0, header_size)
          remainder = buffer.byteslice(header_size, buffer.bytesize - header_size) || "".b
          return parse(block, remainder)
        end

        raise HandshakeError, "HTTP header is too large" if buffer.bytesize >= max_bytes
        remaining = deadline - monotonic_now
        raise HandshakeError, "HTTP upgrade timed out" if remaining <= 0
        wait_until_readable(io, remaining)

        begin
          chunk = io.readpartial([4096, max_bytes + HEADER_END.bytesize].min)
        rescue EOFError
          raise HandshakeError, "connection ended during HTTP upgrade"
        rescue IO::WaitReadable
          next
        end
        raise HandshakeError, "connection ended during HTTP upgrade" if chunk.nil? || chunk.empty?
        buffer << chunk.b
      end
    end

    def parse(bytes, extra_remainder = "".b)
      raise HandshakeError, "HTTP upgrade must be bytes" unless bytes.is_a?(String)
      raw = bytes.b
      boundary = raw.index(HEADER_END)
      raise HandshakeError, "incomplete HTTP header" unless boundary

      header_block = raw.byteslice(0, boundary)
      trailing = raw.byteslice(boundary + HEADER_END.bytesize,
                               raw.bytesize - boundary - HEADER_END.bytesize) || "".b
      reject_bad_line_endings!(raw.byteslice(0, boundary + HEADER_END.bytesize))
      lines = header_block.split("\r\n", -1)
      raise HandshakeError, "missing request line" if lines.empty?

      match = /\A([^ ]+) ([^ ]+) (HTTP\/\d\.\d)\z/.match(lines.shift)
      raise HandshakeError, "malformed request line" unless match
      headers = {}
      lines.each do |line|
        raise HandshakeError, "obsolete folded header" if line.start_with?(" ", "\t")
        colon = line.index(":")
        raise HandshakeError, "malformed header" unless colon && colon > 0
        name = line.byteslice(0, colon)
        raise HandshakeError, "invalid header name" unless TOKEN.match?(name)
        value = line.byteslice(colon + 1, line.bytesize - colon - 1).to_s
        value = value.sub(/\A[ \t]*/, "").sub(/[ \t]*\z/, "")
        reject_control_bytes!(value)
        key = name.downcase
        (headers[key] ||= []) << value.freeze
      end

      UpgradeRequest.new(match[1], match[2], match[3], headers,
                         trailing + extra_remainder.b)
    end

    def validate!(request)
      raise HandshakeError, "upgrade request required" unless request.is_a?(UpgradeRequest)
      raise HandshakeError, "method must be GET" unless request.method == "GET"
      raise HandshakeError, "HTTP/1.1 is required" unless request.version == "HTTP/1.1"

      upgrade = single_header!(request, "upgrade")
      raise HandshakeError, "Upgrade must be websocket" unless upgrade.casecmp("websocket").zero?

      connection_tokens = request.header_values("connection").flat_map do |value|
        value.split(",").map { |token| token.strip.downcase }
      end
      unless connection_tokens.include?("upgrade")
        raise HandshakeError, "Connection must include Upgrade"
      end

      version = single_header!(request, "sec-websocket-version")
      raise HandshakeError, "unsupported WebSocket version" unless version == "13"

      key = single_header!(request, "sec-websocket-key")
      begin
        decoded = Base64.strict_decode64(key)
      rescue ArgumentError
        raise HandshakeError, "invalid WebSocket key"
      end
      canonical = Base64.strict_encode64(decoded)
      unless decoded.bytesize == 16 && canonical == key
        raise HandshakeError, "invalid WebSocket key"
      end
      request
    end

    def single_header!(request, name)
      values = request.header_values(name)
      raise HandshakeError, "missing or duplicate #{name}" unless values.length == 1
      values.first
    end
    private_class_method :single_header!

    def reject_bad_line_endings!(bytes)
      bytes.each_byte.with_index do |byte, index|
        if byte == 10 && (index.zero? || bytes.getbyte(index - 1) != 13)
          raise HandshakeError, "bare LF in HTTP header"
        end
        if byte == 13 && bytes.getbyte(index + 1) != 10
          raise HandshakeError, "bare CR in HTTP header"
        end
      end
    end
    private_class_method :reject_bad_line_endings!

    def reject_control_bytes!(value)
      invalid = value.each_byte.any? do |byte|
        (byte < 32 && byte != 9) || byte == 127
      end
      raise HandshakeError, "control byte in header value" if invalid
    end
    private_class_method :reject_control_bytes!

    def wait_until_readable(io, remaining)
      return unless io.respond_to?(:to_io)
      ready = IO.select([io], nil, nil, remaining)
      raise HandshakeError, "HTTP upgrade timed out" unless ready
    end
    private_class_method :wait_until_readable

    def monotonic_now
      Process.clock_gettime(Process::CLOCK_MONOTONIC)
    end
    private_class_method :monotonic_now
  end
end

