# frozen_string_literal: true

module Pebble
  class Lexer
    def initialize(source)
      @source = source
    end

    def scan_tokens
      raise NotImplementedError, "implement Pebble::Lexer#scan_tokens"
    end
  end
end
