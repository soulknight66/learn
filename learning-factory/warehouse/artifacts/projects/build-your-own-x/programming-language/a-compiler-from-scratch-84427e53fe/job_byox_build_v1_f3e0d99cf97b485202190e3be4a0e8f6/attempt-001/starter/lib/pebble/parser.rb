# frozen_string_literal: true

module Pebble
  class Parser
    def initialize(tokens)
      @tokens = tokens
    end

    def parse
      raise NotImplementedError, "implement Pebble::Parser#parse"
    end
  end
end
