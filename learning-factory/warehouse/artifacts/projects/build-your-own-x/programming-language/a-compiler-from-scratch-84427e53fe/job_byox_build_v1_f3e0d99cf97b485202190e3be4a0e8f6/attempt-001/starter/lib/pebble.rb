# frozen_string_literal: true

require_relative "pebble/errors"
require_relative "pebble/token"
require_relative "pebble/program"
require_relative "pebble/lexer"
require_relative "pebble/parser"
require_relative "pebble/compiler"
require_relative "pebble/vm"

module Pebble
  def self.compile(source)
    tokens = Lexer.new(source).scan_tokens
    ast = Parser.new(tokens).parse
    Compiler.new.compile(ast)
  end

  def self.run(source, output: $stdout, max_steps: 100_000)
    program = compile(source)
    VM.new(program, output: output, max_steps: max_steps).run
  end
end
