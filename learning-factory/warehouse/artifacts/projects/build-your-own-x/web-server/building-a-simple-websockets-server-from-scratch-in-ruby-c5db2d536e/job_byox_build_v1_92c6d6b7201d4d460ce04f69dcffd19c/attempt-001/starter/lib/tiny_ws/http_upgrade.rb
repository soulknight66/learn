# frozen_string_literal: true

module TinyWS
  class UpgradeRequest
    attr_reader :method, :target, :version

    def initialize(method, target, version, headers, remainder = "".b)
      @method = method
      @target = target
      @version = version
      @headers = headers
      @remainder = remainder
    end

    def header(name)
      value = @headers[name.to_s.downcase]
      value.is_a?(Array) && value.length == 1 ? value.first : value
    end

    def header_values(name)
      Array(@headers[name.to_s.downcase]).dup
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
      # TODO: read incrementally, enforce max_bytes/timeout, parse a request,
      # and retain bytes following HEADER_END in UpgradeRequest#take_remainder.
      raise NotImplementedError, "read and parse the HTTP upgrade"
    end

    def parse(bytes, remainder = "".b)
      # TODO: parse one strict HTTP/1.1 header block into UpgradeRequest.
      raise NotImplementedError, "parse the HTTP upgrade"
    end

    def validate!(request)
      # TODO: enforce every handshake rule in REQUIREMENTS.md.
      raise NotImplementedError, "validate the HTTP upgrade"
    end
  end
end

