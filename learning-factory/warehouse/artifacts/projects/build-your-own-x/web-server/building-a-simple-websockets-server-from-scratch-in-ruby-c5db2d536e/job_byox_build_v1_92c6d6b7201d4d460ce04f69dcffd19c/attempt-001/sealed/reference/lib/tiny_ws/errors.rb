# frozen_string_literal: true

module TinyWS
  class HandshakeError < StandardError
  end

  class ProtocolError < StandardError
    attr_reader :close_code

    def initialize(message, close_code = 1002)
      super(message)
      @close_code = close_code
    end
  end

  class LimitError < ProtocolError
    def initialize(message)
      super(message, 1009)
    end
  end
end

