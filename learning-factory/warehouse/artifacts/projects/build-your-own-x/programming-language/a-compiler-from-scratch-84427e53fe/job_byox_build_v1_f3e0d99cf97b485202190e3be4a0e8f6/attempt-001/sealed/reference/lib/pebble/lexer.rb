# frozen_string_literal: true

module Pebble
  class Lexer
    KEYWORDS = {
      "let" => :LET,
      "print" => :PRINT,
      "if" => :IF,
      "else" => :ELSE,
      "while" => :WHILE,
      "true" => :TRUE,
      "false" => :FALSE
    }.freeze

    SINGLE_TOKENS = {
      "+" => :PLUS,
      "-" => :MINUS,
      "*" => :STAR,
      "%" => :PERCENT,
      "(" => :LEFT_PAREN,
      ")" => :RIGHT_PAREN,
      "{" => :LEFT_BRACE,
      "}" => :RIGHT_BRACE,
      ";" => :SEMICOLON
    }.freeze

    MAX_LITERAL = 2_147_483_647

    def initialize(source)
      unless source.is_a?(String)
        raise LexError.new("source must be a String", 1, 1)
      end

      @source = source
      @tokens = []
      @start = 0
      @current = 0
      @line = 1
      @column = 1
      @start_line = 1
      @start_column = 1
    end

    def scan_tokens
      until at_end?
        @start = @current
        @start_line = @line
        @start_column = @column
        scan_token
      end
      @tokens << Token.new(:EOF, "", nil, @line, @column)
      @tokens
    end

    private

    def scan_token
      character = advance
      single_type = SINGLE_TOKENS[character]
      if single_type
        add_token(single_type)
        return
      end

      case character
      when " ", "\t", "\r", "\n"
        return
      when "/"
        if match?("/")
          advance until at_end? || peek == "\n"
        else
          add_token(:SLASH)
        end
      when "!"
        add_token(match?("=") ? :BANG_EQUAL : :BANG)
      when "="
        add_token(match?("=") ? :EQUAL_EQUAL : :EQUAL)
      when "<"
        add_token(match?("=") ? :LESS_EQUAL : :LESS)
      when ">"
        add_token(match?("=") ? :GREATER_EQUAL : :GREATER)
      else
        if digit?(character)
          scan_integer(character)
        elsif identifier_start?(character)
          scan_identifier
        else
          raise LexError.new(
            "unexpected character #{character.inspect}",
            @start_line,
            @start_column
          )
        end
      end
    end

    def scan_integer(first_character)
      advance while digit?(peek)
      lexeme = current_lexeme
      if first_character == "0" && lexeme.length > 1
        raise LexError.new("leading zero in integer literal", @start_line, @start_column)
      end

      value = lexeme.to_i
      if value > MAX_LITERAL
        raise LexError.new("integer literal is out of range", @start_line, @start_column)
      end
      add_token(:INTEGER, value)
    end

    def scan_identifier
      advance while identifier_part?(peek)
      lexeme = current_lexeme
      type = KEYWORDS.fetch(lexeme, :IDENTIFIER)
      literal = if type == :TRUE
                  true
                elsif type == :FALSE
                  false
                end
      add_token(type, literal)
    end

    def advance
      character = @source[@current]
      @current += 1
      if character == "\n"
        @line += 1
        @column = 1
      else
        @column += 1
      end
      character
    end

    def match?(expected)
      return false if at_end? || @source[@current] != expected

      advance
      true
    end

    def peek
      at_end? ? "\0" : @source[@current]
    end

    def at_end?
      @current >= @source.length
    end

    def current_lexeme
      @source[@start...@current]
    end

    def add_token(type, literal = nil)
      @tokens << Token.new(type, current_lexeme, literal, @start_line, @start_column)
    end

    def digit?(character)
      character >= "0" && character <= "9"
    end

    def identifier_start?(character)
      (character >= "a" && character <= "z") ||
        (character >= "A" && character <= "Z") || character == "_"
    end

    def identifier_part?(character)
      identifier_start?(character) || digit?(character)
    end
  end
end
