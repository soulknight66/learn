# frozen_string_literal: true

require "base64"
require "digest/sha1"

module TinyWS
  module Handshake
    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11".freeze
    module_function

    def accept_for(key)
      unless key.is_a?(String) && key.ascii_only?
        raise HandshakeError, "WebSocket key must be ASCII"
      end

      Base64.strict_encode64(Digest::SHA1.digest(key + GUID))
    end

    def response_for(request)
      HTTPUpgrade.validate!(request)
      accept = accept_for(request.header("sec-websocket-key"))
      [
        "HTTP/1.1 101 Switching Protocols",
        "Upgrade: websocket",
        "Connection: Upgrade",
        "Sec-WebSocket-Accept: #{accept}",
        "",
        ""
      ].join("\r\n").b
    end
  end
end

