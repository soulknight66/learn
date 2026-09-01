const PRECEDENCE = Object.freeze({ "+": 30, "-": 30, "*": 20, "/": 20 });

export function toPostfix(tokens) {
  const output = [];
  const operators = [];
  for (const token of tokens) {
    if (typeof token === "number") {
      output.push(token);
      continue;
    }
    if (!Object.prototype.hasOwnProperty.call(PRECEDENCE, token)) {
      throw new TypeError(`Unsupported token: ${String(token)}`);
    }
    while (operators.length > 0 && PRECEDENCE[operators.at(-1)] >= PRECEDENCE[token]) {
      output.push(operators.pop());
    }
    operators.push(token);
  }
  while (operators.length > 0) output.push(operators.pop());
  return output;
}
