# frozen_string_literal: true

module Pebble
  class Compiler
    def compile(ast)
      raise NotImplementedError, "implement Pebble::Compiler#compile"
    end
  end
end
