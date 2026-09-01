# frozen_string_literal: true

module Pebble
  class Parser
    def initialize(tokens)
      @tokens = tokens
      @current = 0
    end

    def parse
      statements = []
      statements << statement until check(:EOF)
      consume(:EOF, "expected end of input")
      fail_at(peek, "unexpected token after EOF") unless @current == @tokens.length
      { type: :program, statements: statements }
    end

    private

    def statement
      return let_statement if match(:LET)
      return print_statement if match(:PRINT)
      return if_statement if match(:IF)
      return while_statement if match(:WHILE)
      return assignment_statement if check(:IDENTIFIER) && check_next(:EQUAL)

      fail_at(peek, "expected a statement")
    end

    def let_statement
      name = consume(:IDENTIFIER, "expected a variable name after 'let'")
      consume(:EQUAL, "expected '=' after variable name")
      value = expression
      consume(:SEMICOLON, "expected ';' after declaration")
      { type: :let, name: name.lexeme, value: value, token: name }
    end

    def assignment_statement
      name = consume(:IDENTIFIER, "expected a variable name")
      consume(:EQUAL, "expected '=' after variable name")
      value = expression
      consume(:SEMICOLON, "expected ';' after assignment")
      { type: :assign, name: name.lexeme, value: value, token: name }
    end

    def print_statement
      token = previous
      value = expression
      consume(:SEMICOLON, "expected ';' after printed expression")
      { type: :print, value: value, token: token }
    end

    def if_statement
      token = previous
      consume(:LEFT_PAREN, "expected '(' after 'if'")
      condition = expression
      consume(:RIGHT_PAREN, "expected ')' after condition")
      then_body = block
      else_body = match(:ELSE) ? block : []
      {
        type: :if,
        condition: condition,
        then_body: then_body,
        else_body: else_body,
        token: token
      }
    end

    def while_statement
      token = previous
      consume(:LEFT_PAREN, "expected '(' after 'while'")
      condition = expression
      consume(:RIGHT_PAREN, "expected ')' after condition")
      { type: :while, condition: condition, body: block, token: token }
    end

    def block
      consume(:LEFT_BRACE, "expected '{' before block")
      statements = []
      until check(:RIGHT_BRACE)
        fail_at(peek, "expected '}' after block") if check(:EOF)
        statements << statement
      end
      consume(:RIGHT_BRACE, "expected '}' after block")
      statements
    end

    def expression
      equality
    end

    def equality
      fold_binary(:comparison, :EQUAL_EQUAL, :BANG_EQUAL)
    end

    def comparison
      fold_binary(:term, :LESS, :LESS_EQUAL, :GREATER, :GREATER_EQUAL)
    end

    def term
      fold_binary(:factor, :PLUS, :MINUS)
    end

    def factor
      fold_binary(:unary, :STAR, :SLASH, :PERCENT)
    end

    def fold_binary(child_method, *operators)
      node = send(child_method)
      while match(*operators)
        operator = previous
        right = send(child_method)
        node = {
          type: :binary,
          operator: operator.type,
          left: node,
          right: right,
          token: operator
        }
      end
      node
    end

    def unary
      if match(:BANG, :MINUS)
        operator = previous
        return {
          type: :unary,
          operator: operator.type,
          operand: unary,
          token: operator
        }
      end
      primary
    end

    def primary
      if match(:INTEGER, :TRUE, :FALSE)
        token = previous
        return { type: :literal, value: token.literal, token: token }
      end
      if match(:IDENTIFIER)
        token = previous
        return { type: :variable, name: token.lexeme, token: token }
      end
      if match(:LEFT_PAREN)
        value = expression
        consume(:RIGHT_PAREN, "expected ')' after expression")
        return value
      end
      fail_at(peek, "expected an expression")
    end

    def match(*types)
      types.each do |type|
        next unless check(type)

        advance
        return true
      end
      false
    end

    def consume(type, message)
      return advance if check(type)

      fail_at(peek, message)
    end

    def check(type)
      token = peek
      token && token.type == type
    end

    def check_next(type)
      token = @tokens[@current + 1]
      token && token.type == type
    end

    def advance
      token = peek
      @current += 1 if token
      token
    end

    def peek
      @tokens[@current]
    end

    def previous
      @tokens[@current - 1]
    end

    def fail_at(token, message)
      if token && token.respond_to?(:line) && token.respond_to?(:column)
        raise ParseError.new(message, token.line, token.column)
      end
      raise ParseError.new(message, 1, 1)
    end
  end
end
