// Evaluator-only sources and expected observations.
export const adversarialCases = [
  {
    id: "empty-program",
    source: "",
    expected: [],
  },
  {
    id: "spacing-comments-and-keyword-prefixes",
    source: `
      // Keywords are recognized only as complete identifiers.
      let whilex = 2;
      let elsewhere = 3;
      set whilex = whilex + elsewhere; // comment at end of statement
      emit whilex;
    `,
    expected: [5],
  },
  {
    id: "precedence-associativity-and-parentheses",
    source: `
      emit 2 + 3 * 4;
      emit (2 + 3) * 4;
      emit 20 - 5 - 3;
      emit 24 / 4 / 3;
    `,
    expected: [14, 20, 12, 2],
  },
  {
    id: "unary-and-decimal-boundaries",
    source: `
      emit - -2;
      emit ! ! true;
      emit 0.5 + 1.25;
    `,
    expected: [2, true, 1.75],
  },
  {
    id: "comparison-and-strict-equality",
    source: `
      emit 1 < 2 == true;
      emit 1 == true;
      emit 1 != true;
      emit 3 >= 3;
    `,
    expected: [true, false, true, true],
  },
  {
    id: "unselected-branch-is-lazy",
    source: `
      let result = 0;
      if false {
        emit 1 / 0;
      } else {
        set result = 7;
        emit result;
      }
    `,
    expected: [7],
  },
  {
    id: "zero-iteration-loop",
    source: `
      let untouched = 9;
      while false {
        set untouched = 0;
        emit untouched;
      }
      emit untouched;
    `,
    expected: [9],
  },
  {
    id: "stateful-counted-loop",
    source: `
      let i = 0;
      let total = 0;
      while i < 5 {
        set total = total + i;
        set i = i + 1;
      }
      emit total;
    `,
    expected: [10],
  },
  {
    id: "nested-loop-back-edges",
    source: `
      let outer = 0;
      let inner = 0;
      let hits = 0;
      while outer < 3 {
        set inner = 0;
        while inner < 2 {
          set hits = hits + 1;
          set inner = inner + 1;
        }
        set outer = outer + 1;
      }
      emit hits;
    `,
    expected: [6],
  },
  {
    id: "prototype-shaped-identifiers",
    source: `
      let constructor = 4;
      let __proto__ = 5;
      emit constructor + __proto__;
    `,
    expected: [9],
  },
  {
    id: "lexer-unknown-character",
    source: "emit 1 & 2;",
    expectedError: { className: "PebbleSyntaxError", code: "UNEXPECTED_CHARACTER" },
  },
  {
    id: "lexer-trailing-decimal-point",
    source: "emit 1.;",
    expectedError: { className: "PebbleSyntaxError", code: "UNEXPECTED_CHARACTER" },
  },
  {
    id: "parser-truncated-expression",
    source: "let value = ;",
    expectedError: { className: "PebbleSyntaxError", code: "UNEXPECTED_TOKEN" },
  },
  {
    id: "parser-missing-semicolon-at-eof",
    source: "emit 1",
    expectedError: { className: "PebbleSyntaxError", code: "UNEXPECTED_TOKEN" },
  },
  {
    id: "false-if-without-else-is-no-op",
    source: "if false { emit 99; } emit 3;",
    expected: [3],
  },
  {
    id: "runtime-undefined-read",
    source: "emit missing;",
    expectedError: { className: "PebbleRuntimeError", code: "UNDEFINED_VARIABLE" },
  },
  {
    id: "runtime-undefined-store",
    source: "set missing = 1;",
    expectedError: { className: "PebbleRuntimeError", code: "UNDEFINED_VARIABLE" },
  },
  {
    id: "runtime-duplicate-declaration",
    source: "let item = 1; let item = 2;",
    expectedError: { className: "PebbleRuntimeError", code: "DUPLICATE_VARIABLE" },
  },
  {
    id: "runtime-division-by-zero",
    source: "emit 8 / 0;",
    expectedError: { className: "PebbleRuntimeError", code: "DIVISION_BY_ZERO" },
  },
  {
    id: "runtime-arithmetic-overflow",
    source: `emit 1${"0".repeat(308)} * 10;`,
    expectedError: { className: "PebbleRuntimeError", code: "NON_FINITE_NUMBER" },
  },
  {
    id: "runtime-condition-must-be-boolean",
    source: "if 1 { emit 1; } else { emit 2; }",
    expectedError: { className: "PebbleRuntimeError", code: "TYPE_ERROR" },
  },
  {
    id: "runtime-unary-type-check",
    source: "emit !1;",
    expectedError: { className: "PebbleRuntimeError", code: "TYPE_ERROR" },
  },
  {
    id: "step-budget-stops-infinite-loop",
    source: "while true { }",
    maxSteps: 24,
    expectedError: { className: "PebbleStepLimitError", code: "STEP_LIMIT_EXCEEDED" },
  },
  {
    id: "step-budget-backend-specific-boundary",
    source: "emit 1;",
    maxSteps: 2,
    allowStepLimitDivergence: true,
    expectedByBackend: {
      tree: { expected: [1] },
      vm: {
        expectedError: { className: "PebbleStepLimitError", code: "STEP_LIMIT_EXCEEDED" },
      },
    },
  },
];
