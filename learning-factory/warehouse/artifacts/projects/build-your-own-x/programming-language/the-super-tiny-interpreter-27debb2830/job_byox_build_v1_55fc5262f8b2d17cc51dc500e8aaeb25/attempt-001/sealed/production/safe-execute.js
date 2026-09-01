import { execute } from "../reference/src/index.js";

const LIMITS = Object.freeze({
  maxSourceLength: 100_000,
  maxTokens: 25_000,
  maxParseDepth: 250,
  maxCompileDepth: 250,
  maxInstructions: 100_000,
  maxConstants: 25_000,
  maxStack: 2_000,
  maxScopes: 250,
  maxSteps: 50_000
});

export function executeWithConservativeLimits(source, engine = "vm") {
  if (typeof source !== "string") throw new TypeError("source must be a string");
  if (engine !== "tree" && engine !== "vm") throw new TypeError("engine must be 'tree' or 'vm'");
  const result = execute(source, { ...LIMITS, engine });
  return Object.freeze({ value: result.value, output: Object.freeze([...result.output]) });
}
