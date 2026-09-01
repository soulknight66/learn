# frozen_string_literal: true

module Pebble
  Token = Struct.new(:type, :lexeme, :literal, :line, :column)
end
