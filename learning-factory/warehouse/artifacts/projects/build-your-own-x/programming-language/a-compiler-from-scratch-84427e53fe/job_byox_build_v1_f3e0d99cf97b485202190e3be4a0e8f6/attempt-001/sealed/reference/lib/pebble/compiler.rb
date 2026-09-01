# frozen_string_literal: true

module Pebble
  class Compiler
    BINARY_OPCODES = {
      PLUS: :ADD,
      MINUS: :SUB,
      STAR: :MUL,
      SLASH: :DIV,
      PERCENT: :MOD,
      EQUAL_EQUAL: :EQ,
      BANG_EQUAL: :NE,
      LESS: :LT,
      LESS_EQUAL: :LE,
      GREATER: :GT,
      GREATER_EQUAL: :GE
    }.freeze

    UNARY_OPCODES = {
      MINUS: :NEG,
      BANG: :NOT
    }.freeze

    def compile(ast)
      @instructions = []
      @scopes = [{}]
      @next_slot = 0

      unless ast.is_a?(Hash) && ast[:type] == :program && ast[:statements].is_a?(Array)
        compile_error("expected a program AST", ast.is_a?(Hash) ? ast[:token] : nil)
      end

      ast[:statements].each { |node| compile_statement(node) }
      emit(:HALT)
      Program.new(@instructions, @next_slot)
    end

    private

    def compile_statement(node)
      validate_node(node)
      case node[:type]
      when :let
        compile_let(node)
      when :assign
        compile_expression(node[:value])
        emit(:STORE, resolve(node[:name], node[:token]))
      when :print
        compile_expression(node[:value])
        emit(:PRINT)
      when :if
        compile_if(node)
      when :while
        compile_while(node)
      else
        compile_error("unknown statement node #{node[:type].inspect}", node[:token])
      end
    end

    def compile_let(node)
      name = validate_name(node[:name], node[:token])
      if @scopes.last.key?(name)
        compile_error("variable '#{name}' is already declared in this scope", node[:token])
      end

      compile_expression(node[:value])
      slot = @next_slot
      @next_slot += 1
      @scopes.last[name] = slot
      emit(:STORE, slot)
    end

    def compile_if(node)
      compile_expression(node[:condition])
      false_jump = emit(:JUMP_IF_FALSE, nil)
      compile_block(node[:then_body], node[:token])

      else_body = node[:else_body]
      unless else_body.is_a?(Array)
        compile_error("if else_body must be an Array", node[:token])
      end
      if else_body.empty?
        patch_jump(false_jump, @instructions.length)
      else
        end_jump = emit(:JUMP, nil)
        patch_jump(false_jump, @instructions.length)
        compile_block(else_body, node[:token])
        patch_jump(end_jump, @instructions.length)
      end
    end

    def compile_while(node)
      loop_start = @instructions.length
      compile_expression(node[:condition])
      exit_jump = emit(:JUMP_IF_FALSE, nil)
      compile_block(node[:body], node[:token])
      emit(:JUMP, loop_start)
      patch_jump(exit_jump, @instructions.length)
    end

    def compile_block(statements, token)
      unless statements.is_a?(Array)
        compile_error("block body must be an Array", token)
      end

      @scopes << {}
      begin
        statements.each { |statement| compile_statement(statement) }
      ensure
        @scopes.pop
      end
    end

    def compile_expression(node)
      validate_node(node)
      case node[:type]
      when :literal
        value = node[:value]
        unless value.is_a?(Integer) || value.equal?(true) || value.equal?(false)
          compile_error("invalid literal", node[:token])
        end
        emit(:CONST, value)
      when :variable
        emit(:LOAD, resolve(node[:name], node[:token]))
      when :unary
        opcode = UNARY_OPCODES[node[:operator]]
        compile_error("unknown unary operator", node[:token]) unless opcode
        compile_expression(node[:operand])
        emit(opcode)
      when :binary
        opcode = BINARY_OPCODES[node[:operator]]
        compile_error("unknown binary operator", node[:token]) unless opcode
        compile_expression(node[:left])
        compile_expression(node[:right])
        emit(opcode)
      else
        compile_error("unknown expression node #{node[:type].inspect}", node[:token])
      end
    end

    def resolve(name, token)
      name = validate_name(name, token)
      (@scopes.length - 1).downto(0) do |index|
        return @scopes[index][name] if @scopes[index].key?(name)
      end
      compile_error("variable '#{name}' is not declared", token)
    end

    def validate_name(name, token)
      return name if name.is_a?(String) && name.match?(/\A[A-Za-z_][A-Za-z0-9_]*\z/)

      compile_error("invalid variable name", token)
    end

    def validate_node(node)
      return if node.is_a?(Hash)

      compile_error("expected an AST node", nil)
    end

    def emit(opcode, *operands)
      index = @instructions.length
      @instructions << [opcode, *operands]
      index
    end

    def patch_jump(index, target)
      @instructions[index][1] = target
    end

    def compile_error(message, token)
      if token && token.respond_to?(:line) && token.respond_to?(:column)
        raise CompileError.new(message, token.line, token.column)
      end
      raise CompileError.new(message, 1, 1)
    end
  end
end
