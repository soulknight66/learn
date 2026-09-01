# frozen_string_literal: true

require "stringio"
require_relative "support/harness"

candidate_lib = ENV["PEBBLE_LIB"] || File.expand_path("../starter/lib", __dir__)
$LOAD_PATH.unshift(candidate_lib)
require "pebble"

class PebblePublicTest < PublicTest::Case
  def token_types(source)
    Pebble::Lexer.new(source).scan_tokens.map(&:type)
  end

  def execute(source, max_steps: 100_000)
    output = StringIO.new
    result = Pebble.run(source, output: output, max_steps: max_steps)
    assert_nil result
    output.string
  end

  def test_lexer_tracks_tokens_comments_and_positions
    source = "let x = 12;\n// ignored\nprint x != 3;"
    tokens = Pebble::Lexer.new(source).scan_tokens
    assert_equal(
      [:LET, :IDENTIFIER, :EQUAL, :INTEGER, :SEMICOLON,
       :PRINT, :IDENTIFIER, :BANG_EQUAL, :INTEGER, :SEMICOLON, :EOF],
      tokens.map(&:type)
    )
    assert_equal [12, true], [tokens[3].literal, tokens[7].lexeme == "!="]
    assert_equal [3, 1], [tokens[5].line, tokens[5].column]
  end

  def test_lexer_rejects_leading_zero_integer
    error = assert_raises(Pebble::LexError) do
      Pebble::Lexer.new("print 01;").scan_tokens
    end
    assert_match(/1:7/, error.message)
  end

  def test_parser_encodes_precedence_in_ast
    tokens = Pebble::Lexer.new("print 1 + 2 * 3 == 7;").scan_tokens
    ast = Pebble::Parser.new(tokens).parse
    expression = ast.fetch(:statements).first.fetch(:value)
    assert_equal :binary, expression.fetch(:type)
    assert_equal :EQUAL_EQUAL, expression.fetch(:operator)
    assert_equal :PLUS, expression.fetch(:left).fetch(:operator)
    assert_equal :STAR, expression.fetch(:left).fetch(:right).fetch(:operator)
  end

  def test_parser_reports_missing_semicolon_location
    error = assert_raises(Pebble::ParseError) do
      Pebble::Parser.new(Pebble::Lexer.new("print 1").scan_tokens).parse
    end
    assert_match(/1:8/, error.message)
  end

  def test_compiler_emits_deterministic_straight_line_bytecode
    ast = Pebble::Parser.new(
      Pebble::Lexer.new("let x = 2; print x + 3;").scan_tokens
    ).parse
    program = Pebble::Compiler.new.compile(ast)
    assert_equal 1, program.local_count
    assert_equal [
      [:CONST, 2], [:STORE, 0], [:LOAD, 0], [:CONST, 3],
      [:ADD], [:PRINT], [:HALT]
    ], program.instructions
  end

  def test_nested_declaration_shadows_without_overwriting_outer_value
    source = <<~PEBBLE
      let x = 1;
      if (true) {
        let x = 2;
        print x;
      } else {
        print 99;
      }
      print x;
    PEBBLE
    assert_equal "2\n1\n", execute(source)
  end

  def test_loop_and_assignment_compute_factorial
    source = <<~PEBBLE
      let n = 5;
      let product = 1;
      while (n > 1) {
        product = product * n;
        n = n - 1;
      }
      print product;
    PEBBLE
    assert_equal "120\n", execute(source)
  end

  def test_undeclared_assignment_is_compile_error
    error = assert_raises(Pebble::CompileError) do
      Pebble.compile("missing = 4;")
    end
    assert_match(/1:1/, error.message)
  end

  def test_runtime_types_are_exact
    assert_raises(Pebble::VMError) { execute("print 1 + true;") }
    assert_raises(Pebble::VMError) { execute("if (1) { print 2; }") }
  end

  def test_division_and_modulo_truncate_toward_zero
    assert_equal "-2\n-1\n", execute("print -7 / 3; print -7 % 3;")
  end

  def test_arithmetic_overflow_is_rejected
    assert_raises(Pebble::VMError) do
      execute("print 2147483647 + 1;")
    end
  end

  def test_vm_rejects_bad_bytecode_and_limits_steps
    assert_raises(Pebble::VMError) do
      Pebble::VM.new(Pebble::Program.new([[:CONST], [:HALT]], 0)).run
    end
    assert_raises(Pebble::VMError) do
      looping = Pebble::Program.new([[:JUMP, 0], [:HALT]], 0)
      Pebble::VM.new(looping, max_steps: 4).run
    end
  end
end

PebblePublicTest.run!
