# frozen_string_literal: true

module Pebble
  class Error < StandardError
  end

  class SourceError < Error
    attr_reader :line, :column

    def initialize(message, line, column)
      @line = line
      @column = column
      super("#{line}:#{column}: #{message}")
    end
  end

  class LexError < SourceError
  end

  class ParseError < SourceError
  end

  class CompileError < SourceError
  end

  class VMError < Error
  end
end
