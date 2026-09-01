import { createHash } from "node:crypto";
import { lstatSync, readdirSync, readFileSync } from "node:fs";
import { dirname, relative, resolve, sep } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const PACK_ROOT = resolve(HERE, "../..");
const CANDIDATE_ROOT = resolve(PACK_ROOT, "starter");
const ORACLE_ROOT = resolve(PACK_ROOT, "sealed/reference");
const CANDIDATE_ENTRY = resolve(CANDIDATE_ROOT, "src/index.js");
const ORACLE_ENTRY = resolve(ORACLE_ROOT, "index.js");

const REQUIRED_EXPORTS = Object.freeze([
  "PebbleRuntimeError",
  "PebbleStepLimitError",
  "PebbleSyntaxError",
  "compile",
  "evaluate",
  "execute",
  "parse",
  "run",
  "tokenize",
]);

function isInside(root, target) {
  return target === root || target.startsWith(`${root}${sep}`);
}

function regularFiles(root) {
  const result = [];
  const visit = (directory) => {
    const entries = readdirSync(directory, { withFileTypes: true })
      .sort((left, right) => (left.name < right.name ? -1 : left.name > right.name ? 1 : 0));
    for (const entry of entries) {
      const absolute = resolve(directory, entry.name);
      if (!isInside(root, absolute)) throw new Error("artifact walk escaped its fixed root");
      if (entry.isSymbolicLink()) {
        throw new Error(`artifact contains a symbolic link: ${relative(root, absolute)}`);
      }
      if (entry.isDirectory()) {
        visit(absolute);
      } else if (entry.isFile()) {
        result.push(absolute);
      } else {
        throw new Error(`artifact contains a special path: ${relative(root, absolute)}`);
      }
    }
  };

  if (!lstatSync(root).isDirectory()) throw new Error("artifact root is not a directory");
  visit(root);
  return result.sort((left, right) => {
    const leftName = portableRelative(root, left);
    const rightName = portableRelative(root, right);
    return leftName < rightName ? -1 : leftName > rightName ? 1 : 0;
  });
}

function portableRelative(root, absolute) {
  return relative(root, absolute).split(sep).join("/");
}

function treeIdentity(role, root, entry) {
  const records = regularFiles(root).map((absolute) => {
    const content = readFileSync(absolute);
    return [portableRelative(root, absolute), createHash("sha256").update(content).digest("hex")];
  });
  const sha256 = createHash("sha256").update(JSON.stringify(records)).digest("hex");
  return Object.freeze({
    role,
    algorithm: "path-content-sha256-v1",
    root: portableRelative(PACK_ROOT, root),
    entry: portableRelative(PACK_ROOT, entry),
    files: records.length,
    sha256,
  });
}

function candidateBoundaryViolations() {
  const violations = [];
  const fromPattern = /\b(?:from)\s*["']([^"']+)["']/g;
  const sideEffectPattern = /\bimport\s*["']([^"']+)["']/g;
  const dynamicPattern = /\bimport\s*\(/;

  for (const absolute of regularFiles(CANDIDATE_ROOT)) {
    if (!absolute.endsWith(".js") && !absolute.endsWith(".mjs")) continue;
    const source = readFileSync(absolute, "utf8");
    const display = portableRelative(PACK_ROOT, absolute);
    if (dynamicPattern.test(source)) violations.push(`${display}: dynamic import is not allowed`);

    const specifiers = [];
    for (const pattern of [fromPattern, sideEffectPattern]) {
      pattern.lastIndex = 0;
      for (let match = pattern.exec(source); match !== null; match = pattern.exec(source)) {
        specifiers.push(match[1]);
      }
    }
    for (const specifier of specifiers) {
      if (!specifier.startsWith(".") || specifier.includes("?") || specifier.includes("#")) {
        violations.push(`${display}: non-local module specifier ${JSON.stringify(specifier)}`);
        continue;
      }
      const target = resolve(dirname(absolute), specifier);
      if (!isInside(CANDIDATE_ROOT, target)) {
        violations.push(`${display}: module specifier escapes starter/: ${JSON.stringify(specifier)}`);
      }
    }
  }
  return violations;
}

function assertApi(role, api) {
  for (const name of REQUIRED_EXPORTS) {
    if (typeof api[name] !== "function") {
      throw new Error(`${role} module is missing required function/class export ${name}`);
    }
  }
}

function identities() {
  return Object.freeze({
    candidate: treeIdentity("candidate", CANDIDATE_ROOT, CANDIDATE_ENTRY),
    oracle: treeIdentity("oracle", ORACLE_ROOT, ORACLE_ENTRY),
  });
}

/**
 * Load the fixed learner module and sealed oracle only after checking the candidate tree.
 * No command-line argument or environment variable can select either entry point.
 */
export async function loadImplementations({ reportArtifacts = () => {} } = {}) {
  if (typeof reportArtifacts !== "function") throw new TypeError("reportArtifacts must be a function");
  const violations = candidateBoundaryViolations();
  if (violations.length > 0) {
    throw new Error(`candidate module boundary rejected:\n${violations.join("\n")}`);
  }

  const before = identities();
  reportArtifacts(before);
  const [candidate, oracle] = await Promise.all([
    import(pathToFileURL(CANDIDATE_ENTRY).href),
    import(pathToFileURL(ORACLE_ENTRY).href),
  ]);
  const after = identities();
  if (before.candidate.sha256 !== after.candidate.sha256
      || before.oracle.sha256 !== after.oracle.sha256) {
    throw new Error("candidate or oracle artifact changed while its module was loading");
  }
  assertApi("candidate", candidate);
  assertApi("oracle", oracle);
  return Object.freeze({ candidate, oracle, artifacts: after });
}
