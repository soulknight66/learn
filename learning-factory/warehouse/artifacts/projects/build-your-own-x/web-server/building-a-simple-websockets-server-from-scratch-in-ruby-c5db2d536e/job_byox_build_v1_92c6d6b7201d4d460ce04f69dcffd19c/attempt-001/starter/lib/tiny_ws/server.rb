# frozen_string_literal: true

require "socket"

module TinyWS
  class Server
    DEFAULTS = {
      host: "127.0.0.1",
      port: 8080,
      max_clients: 32,
      max_header_bytes: 16_384,
      max_frame_bytes: 1_048_576,
      max_message_bytes: 4_194_304,
      handshake_timeout: 5.0,
      read_timeout: 30.0
    }.freeze

    def initialize(**options, &handler)
      @options = DEFAULTS.merge(options)
      @handler = handler || proc { |_type, payload| payload }
      @listener = nil
    end

    def start
      # TODO: bind, start a bounded accept loop, and return self.
      raise NotImplementedError, "start the WebSocket server"
    end

    def port
      # TODO: report the actual port after binding (including port 0).
      @options[:port]
    end

    def stop
      # TODO: make shutdown idempotent and bounded.
      self
    end

    def serve_forever
      start
      sleep 0.05 while @listener
    ensure
      stop
    end
  end
end

