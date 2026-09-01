# frozen_string_literal: true

require "stringio"
require_relative "../../public_tests/support/harness"

$LOAD_PATH.unshift(File.expand_path("../reference/lib", __dir__))
require "pebble"

class PebbleReferenceTest < PublicTest::Case
  def lex(source)
    Pebble::Lexer.new(source).scan_tokens
  end

  def parse(source)
    Pebble::Parser.new(lex(source)).parse
  end

  def execute(source, max_steps: 100_000)
    output = StringIO.new
    result = Pebble.run(source, output: output, max_steps: max_steps)
    assert_nil result
    output.string
  end

  def run_program(instructions, local_count = 0, max_steps: 100)
    output = StringIO.new
    program = Pebble::Program.new(instructions, local_count)
    result = Pebble::VM.new(program, output: output, max_steps: max_steps).run
    assert_nil result
    output.string
  end

  def test_empty_input_has_only_positioned_eof
    tokens = lex("")
    assert_equal 1, tokens.length
    assert_equal [:EOF, "", nil, 1, 1], tokens.first.to_a
    assert_equal({ type: :program, statements: [] }, parse(""))
  end

  def test_lexer_recognizes_every_operator_with_longest_match
    source = "+ - * / % ! != = == < <= > >= ( ) { } ;"
    expected = [
      :PLUS, :MINUS, :STAR, :SLASH, :PERCENT, :BANG, :BANG_EQUAL,
      :EQUAL, :EQUAL_EQUAL, :LESS, :LESS_EQUAL, :GREATER, :GREATER_EQUAL,
      :LEFT_PAREN, :RIGHT_PAREN, :LEFT_BRACE, :RIGHT_BRACE, :SEMICOLON, :EOF
    ]
    assert_equal expected, lex(source).map(&:type)
  end

  def test_lexer_distinguishes_keywords_identifiers_and_literals
    tokens = lex("let letter print if else while true false true_value _x x2")
    assert_equal [
      :LET, :IDENTIFIER, :PRINT, :IF, :ELSE, :WHILE, :TRUE, :FALSE,
      :IDENTIFIER, :IDENTIFIER, :IDENTIFIER, :EOF
    ], tokens.map(&:type)
    assert_equal [true, false], [tokens[6].literal, tokens[7].literal]
  end

  def test_lexer_tracks_newlines_inside_comments
    tokens = lex("// first\n\n  print\t0;// tail")
    assert_equal [:PRINT, :INTEGER, :SEMICOLON, :EOF], tokens.map(&:type)
    assert_equal [3, 3], [tokens.first.line, tokens.first.column]
    assert_equal [3, 18], [tokens.last.line, tokens.last.column]
  end

  def test_lexer_rejects_invalid_source_and_integers
    assert_raises(Pebble::LexError) { lex("@") }
    assert_raises(Pebble::LexError) { lex("00") }
    assert_raises(Pebble::LexError) { lex("2147483648") }
    assert_raises(Pebble::LexError) { Pebble::Lexer.new(nil) }
    assert_equal 0, lex("0").first.literal
  end

  def test_parser_builds_left_associative_binary_trees
    value = parse("print 10 - 3 - 2;")[:statements][0][:value]
    assert_equal :MINUS, value[:operator]
    assert_equal :MINUS, value[:left][:operator]
    assert_equal 2, value[:right][:value]
  end

  def test_parser_nests_unary_operators
    value = parse("print !-1;")[:statements][0][:value]
    assert_equal [:unary, :BANG], [value[:type], value[:operator]]
    assert_equal [:unary, :MINUS], [value[:operand][:type], value[:operand][:operator]]
  end

  def test_parser_accepts_empty_required_blocks
    statements = parse("if (false) {} else {} while (false) {}")[:statements]
    assert_equal [:if, :while], statements.map { |node| node[:type] }
    assert_equal [], statements.first[:then_body]
    assert_equal [], statements.first[:else_body]
  end

  def test_parser_rejects_bare_or_unterminated_blocks
    assert_raises(Pebble::ParseError) { parse("{ print 1; }") }
    error = assert_raises(Pebble::ParseError) { parse("while (true) { print 1;") }
    assert_match(/1:24/, error.message)
  end

  def test_parser_rejects_tokens_after_eof
    eof = Pebble::Token.new(:EOF, "", nil, 1, 1)
    extra = Pebble::Token.new(:INTEGER, "1", 1, 1, 1)
    assert_raises(Pebble::ParseError) { Pebble::Parser.new([eof, extra]).parse }
  end

  def test_compiler_rejects_duplicate_and_unknown_names
    assert_raises(Pebble::CompileError) { Pebble.compile("let x = 1; let x = 2;") }
    assert_raises(Pebble::CompileError) { Pebble.compile("print absent;") }
    assert_raises(Pebble::CompileError) { Pebble.compile("absent = 3;") }
  end

  def test_declaration_initializer_can_see_outer_but_not_itself
    source = "let x = 4; if (true) { let x = x + 1; print x; } print x;"
    assert_equal "5\n4\n", execute(source)
    assert_raises(Pebble::CompileError) { Pebble.compile("let x = x;") }
  end

  def test_block_local_is_not_visible_after_block
    source = "if (true) { let local = 1; print local; } print local;"
    assert_raises(Pebble::CompileError) { Pebble.compile(source) }
  end

  def test_compiler_instance_resets_and_is_deterministic
    compiler = Pebble::Compiler.new
    ast = parse("let a = 1; print a;")
    first = compiler.compile(ast)
    second = compiler.compile(ast)
    assert_equal first.instructions, second.instructions
    assert_equal 1, second.local_count
  end

  def test_nested_scopes_receive_distinct_stable_slots
    program = Pebble.compile(
      "let x = 0; if (true) { let y = 1; print y; } else { let z = 2; print z; }"
    )
    stores = program.instructions.select { |instruction| instruction[0] == :STORE }
    assert_equal [0, 1, 2], stores.map { |instruction| instruction[1] }
    assert_equal 3, program.local_count
  end

  def test_if_selects_exactly_one_branch
    assert_equal "1\n", execute("if (true) { print 1; } else { print 2; }")
    assert_equal "2\n", execute("if (false) { print 1; } else { print 2; }")
  end

  def test_while_may_execute_zero_or_many_times
    assert_equal "0\n", execute("let x = 0; while (false) { x = 9; } print x;")
    source = "let x = 3; while (x > 0) { print x; x = x - 1; }"
    assert_equal "3\n2\n1\n", execute(source)
  end

  def test_arithmetic_and_comparison_operators
    source = <<~PEBBLE
      print 6 + 2;
      print 6 - 2;
      print 6 * 2;
      print 7 / 2;
      print 7 % 2;
      print 2 < 3;
      print 2 <= 2;
      print 3 > 2;
      print 3 >= 3;
    PEBBLE
    assert_equal "8\n4\n12\n3\n1\ntrue\ntrue\ntrue\ntrue\n", execute(source)
  end

  def test_division_and_modulo_all_sign_combinations
    source = <<~PEBBLE
      print 7 / -3; print 7 % -3;
      print -7 / 3; print -7 % 3;
      print -7 / -3; print -7 % -3;
    PEBBLE
    assert_equal "-2\n1\n-2\n-1\n2\n-1\n", execute(source)
  end

  def test_equality_preserves_pebble_type_identity
    source = "print 1 == 1; print 1 != 2; print true == true; print true == 1;"
    assert_equal "true\ntrue\ntrue\nfalse\n", execute(source)
  end

  def test_runtime_rejects_zero_divisors_and_wrong_types
    assert_raises(Pebble::VMError) { execute("print 1 / 0;") }
    assert_raises(Pebble::VMError) { execute("print 1 % 0;") }
    assert_raises(Pebble::VMError) { execute("print !0;") }
    assert_raises(Pebble::VMError) { execute("while (1) {}") }
  end

  def test_runtime_rejects_every_arithmetic_overflow_shape
    assert_raises(Pebble::VMError) { execute("print 2147483647 + 1;") }
    assert_raises(Pebble::VMError) { execute("print -2147483647 - 2;") }
    assert_raises(Pebble::VMError) { execute("print 50000 * 50000;") }
    assert_raises(Pebble::VMError) do
      run_program([[:CONST, -2_147_483_648], [:NEG], [:PRINT], [:HALT]])
    end
    assert_raises(Pebble::VMError) do
      run_program([[:CONST, -2_147_483_648], [:CONST, -1], [:DIV], [:PRINT], [:HALT]])
    end
  end

  def test_vm_validates_instruction_shape_opcode_and_operands
    boolean_impostor = Object.new
    def boolean_impostor.==(other)
      other.equal?(true)
    end
    assert_raises(Pebble::VMError) { run_program([[:NOPE], [:HALT]]) }
    assert_raises(Pebble::VMError) { run_program([[:CONST], [:HALT]]) }
    assert_raises(Pebble::VMError) { run_program([[:CONST, Object.new], [:HALT]]) }
    assert_raises(Pebble::VMError) { run_program([[:CONST, boolean_impostor], [:HALT]]) }
    assert_raises(Pebble::VMError) { run_program([[:JUMP, 9], [:HALT]]) }
    assert_raises(Pebble::VMError) { run_program([[:LOAD, 0], [:HALT]], 0) }
    assert_raises(Pebble::VMError) { run_program(["HALT"]) }
  end

  def test_vm_detects_stack_and_local_failures
    assert_raises(Pebble::VMError) { run_program([[:PRINT], [:HALT]]) }
    assert_raises(Pebble::VMError) { run_program([[:LOAD, 0], [:HALT]], 1) }
    assert_raises(Pebble::VMError) { run_program([[:CONST, 1], [:HALT]]) }
  end

  def test_vm_requires_halt_and_can_detect_fallthrough
    assert_raises(Pebble::VMError) { run_program([[:CONST, 1]]) }
    assert_raises(Pebble::VMError) do
      run_program([[:JUMP, 2], [:HALT], [:CONST, 1]])
    end
  end

  def test_vm_validates_budget_and_output_and_stops_infinite_loop
    program = Pebble::Program.new([[:HALT]], 0)
    assert_raises(Pebble::VMError) { Pebble::VM.new(program, max_steps: 0).run }
    assert_raises(Pebble::VMError) { Pebble::VM.new(program, output: Object.new).run }
    assert_raises(Pebble::VMError) do
      run_program([[:JUMP, 0], [:HALT]], 0, max_steps: 3)
    end
  end

  def test_vm_executes_well_formed_manual_locals
    instructions = [
      [:CONST, 41], [:STORE, 0], [:LOAD, 0], [:CONST, 1],
      [:ADD], [:PRINT], [:HALT]
    ]
    assert_equal "42\n", run_program(instructions, 1)
  end
end

PebbleReferenceTest.run!
