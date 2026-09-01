# frozen_string_literal: true

module Pebble
  class VM
    def initialize(program, output: $stdout, max_steps: 100_000)
      @program = program
      @output = output
      @max_steps = max_steps
    end

    def run
      raise NotImplementedError, "implement Pebble::VM#run"
    end
  end
end
