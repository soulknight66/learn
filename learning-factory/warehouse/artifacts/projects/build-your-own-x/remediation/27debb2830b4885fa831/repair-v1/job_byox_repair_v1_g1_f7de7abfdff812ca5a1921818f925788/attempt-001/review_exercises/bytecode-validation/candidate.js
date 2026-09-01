const KNOWN = new Set(["CONSTANT", "ADD", "PRINT", "JUMP", "HALT"]);

export function looksValid(program) {
  if (!program || program.version !== 1) return false;
  if (!Array.isArray(program.constants) || !Array.isArray(program.code)) return false;
  if (program.code.length === 0 || program.code.at(-1)?.op !== "HALT") return false;
  return program.code.every((instruction) => KNOWN.has(instruction?.op));
}
