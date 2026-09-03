import { readFileSync } from "node:fs";
import { execute } from "./pipeline.mjs";

function parseArguments(arguments_) {
  let backend = "tree";
  let file = null;
  for (let index = 0; index < arguments_.length; index += 1) {
    if (arguments_[index] === "--backend") {
      if (index + 1 >= arguments_.length) throw new Error("--backend needs tree or vm");
      backend = arguments_[index + 1];
      index += 1;
    } else if (file === null) {
      file = arguments_[index];
    } else {
      throw new Error("expected at most one source file");
    }
  }
  return { backend, file };
}

try {
  const { backend, file } = parseArguments(process.argv.slice(2));
  const source = readFileSync(file ?? 0, "utf8");
  const result = execute(source, { backend });
  for (const line of result.output) console.log(line);
} catch (error) {
  const code = typeof error?.code === "string" ? `${error.code}: ` : "";
  const location = error?.span?.start
    ? ` (${error.span.start.line}:${error.span.start.column})`
    : "";
  console.error(`${code}${error.message}${location}`);
  process.exitCode = 1;
}
