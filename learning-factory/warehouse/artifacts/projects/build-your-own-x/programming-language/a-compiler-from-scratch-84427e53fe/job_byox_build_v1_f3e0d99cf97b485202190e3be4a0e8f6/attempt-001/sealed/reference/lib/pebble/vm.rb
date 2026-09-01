# frozen_string_literal: true

module Pebble
  class VM
    MIN_INTEGER = -2_147_483_648
    MAX_INTEGER = 2_147_483_647
    UNINITIALIZED = Object.new.freeze

    ARITIES = {
      CONST: 1,
      LOAD: 1,
      STORE: 1,
      ADD: 0,
      SUB: 0,
      MUL: 0,
      DIV: 0,
      MOD: 0,
      NEG: 0,
      NOT: 0,
      EQ: 0,
      NE: 0,
      LT: 0,
      LE: 0,
      GT: 0,
      GE: 0,
      PRINT: 0,
      JUMP: 1,
      JUMP_IF_FALSE: 1,
      HALT: 0
    }.freeze

    def initialize(program, output: $stdout, max_steps: 100_000)
      @program = program
      @output = output
      @max_steps = max_steps
    end

    def run
      validate_program
      stack = []
      locals = Array.new(@local_count, UNINITIALIZED)
      ip = 0
      steps = 0

      while ip < @instructions.length
        raise VMError, "instruction step limit exceeded" if steps >= @max_steps

        instruction = @instructions[ip]
        opcode = instruction[0]
        operand = instruction[1]
        steps += 1

        case opcode
        when :CONST
          stack << operand
          ip += 1
        when :LOAD
          value = locals[operand]
          raise VMError, "read from uninitialized local #{operand}" if value.equal?(UNINITIALIZED)

          stack << value
          ip += 1
        when :STORE
          locals[operand] = pop_value(stack, opcode)
          ip += 1
        when :ADD, :SUB, :MUL, :DIV, :MOD
          right, left = pop_integer_pair(stack, opcode)
          stack << checked_arithmetic(opcode, left, right)
          ip += 1
        when :NEG
          value = require_integer(pop_value(stack, opcode), opcode)
          stack << checked_integer(-value)
          ip += 1
        when :NOT
          value = require_boolean(pop_value(stack, opcode), opcode)
          stack << !value
          ip += 1
        when :EQ, :NE
          right = pop_value(stack, opcode)
          left = pop_value(stack, opcode)
          equal = equal_values?(left, right)
          stack << (opcode == :EQ ? equal : !equal)
          ip += 1
        when :LT, :LE, :GT, :GE
          right, left = pop_integer_pair(stack, opcode)
          stack << compare(opcode, left, right)
          ip += 1
        when :PRINT
          @output.write(format_value(pop_value(stack, opcode)) + "\n")
          ip += 1
        when :JUMP
          ip = operand
        when :JUMP_IF_FALSE
          condition = require_boolean(pop_value(stack, opcode), opcode)
          ip = condition ? ip + 1 : operand
        when :HALT
          raise VMError, "nonempty stack at HALT" unless stack.empty?

          return nil
        end
      end

      raise VMError, "execution reached the end without HALT"
    end

    private

    def validate_program
      unless @max_steps.is_a?(Integer) && @max_steps.positive?
        raise VMError, "max_steps must be a positive Integer"
      end
      unless @output.respond_to?(:write)
        raise VMError, "output must respond to write"
      end
      unless @program.respond_to?(:instructions) && @program.respond_to?(:local_count)
        raise VMError, "invalid program object"
      end

      instructions = @program.instructions
      @local_count = @program.local_count
      unless instructions.is_a?(Array) && @local_count.is_a?(Integer) && @local_count >= 0
        raise VMError, "invalid program containers"
      end
      raise VMError, "program has no instructions" if instructions.empty?

      instructions.each_with_index do |instruction, index|
        validate_instruction(instruction, index, instructions.length)
      end
      unless instructions.any? { |instruction| instruction[0] == :HALT }
        raise VMError, "program has no HALT instruction"
      end

      @instructions = instructions.map(&:dup)
    end

    def validate_instruction(instruction, index, instruction_count)
      unless instruction.is_a?(Array) && instruction[0].is_a?(Symbol)
        raise VMError, "invalid instruction at #{index}"
      end

      opcode = instruction[0]
      unless ARITIES.key?(opcode)
        raise VMError, "unknown opcode #{opcode.inspect} at #{index}"
      end
      unless instruction.length == ARITIES[opcode] + 1
        raise VMError, "wrong operand count for #{opcode} at #{index}"
      end

      operand = instruction[1]
      case opcode
      when :CONST
        unless valid_value?(operand)
          raise VMError, "invalid constant at #{index}"
        end
      when :LOAD, :STORE
        unless operand.is_a?(Integer) && operand >= 0 && operand < @local_count
          raise VMError, "invalid local index at #{index}"
        end
      when :JUMP, :JUMP_IF_FALSE
        unless operand.is_a?(Integer) && operand >= 0 && operand < instruction_count
          raise VMError, "invalid jump target at #{index}"
        end
      end
    end

    def pop_value(stack, opcode)
      raise VMError, "stack underflow in #{opcode}" if stack.empty?

      stack.pop
    end

    def pop_integer_pair(stack, opcode)
      right = require_integer(pop_value(stack, opcode), opcode)
      left = require_integer(pop_value(stack, opcode), opcode)
      [right, left]
    end

    def require_integer(value, opcode)
      return value if value.is_a?(Integer)

      raise VMError, "#{opcode} requires integer operands"
    end

    def require_boolean(value, opcode)
      return value if boolean?(value)

      raise VMError, "#{opcode} requires a boolean operand"
    end

    def checked_arithmetic(opcode, left, right)
      result = case opcode
               when :ADD then left + right
               when :SUB then left - right
               when :MUL then left * right
               when :DIV then truncate_division(left, right)
               when :MOD
                 quotient = truncate_division(left, right)
                 left - quotient * right
               end
      checked_integer(result)
    end

    def truncate_division(left, right)
      raise VMError, "division by zero" if right.zero?

      magnitude = left.abs / right.abs
      (left.negative? ^ right.negative?) ? -magnitude : magnitude
    end

    def checked_integer(value)
      unless value >= MIN_INTEGER && value <= MAX_INTEGER
        raise VMError, "integer overflow"
      end
      value
    end

    def compare(opcode, left, right)
      case opcode
      when :LT then left < right
      when :LE then left <= right
      when :GT then left > right
      when :GE then left >= right
      end
    end

    def equal_values?(left, right)
      return left == right if left.is_a?(Integer) && right.is_a?(Integer)
      return left == right if boolean?(left) && boolean?(right)

      false
    end

    def valid_value?(value)
      boolean?(value) ||
        (value.is_a?(Integer) && value >= MIN_INTEGER && value <= MAX_INTEGER)
    end

    def boolean?(value)
      value.equal?(true) || value.equal?(false)
    end

    def format_value(value)
      return "true" if value.equal?(true)
      return "false" if value.equal?(false)
      return value.to_s if value.is_a?(Integer)

      raise VMError, "cannot print invalid value"
    end
  end
end
