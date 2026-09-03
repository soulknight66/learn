import { createHash } from "node:crypto";
import { lstat, readFile, readdir } from "node:fs/promises";
import { dirname, isAbsolute, join, posix, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const packRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const policyPath = "environment/learner-view-policy.json";
const hostOwnedTopLevel = new Set([
  ".agents",
  ".codex",
  ".factory-workspace",
  "PRIOR_BUILD",
  "PRIOR_REVIEW",
]);

function fail(message) {
  throw new Error(`learner-view policy violation: ${message}`);
}

function assertStringArray(value, label) {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string" || item.length === 0)) {
    fail(`${label} must be an array of non-empty strings`);
  }
  if (new Set(value).size !== value.length) fail(`${label} contains a duplicate`);
}

export function validatePolicy(policy) {
  const expectedKeys = ["exclude", "include", "name", "schema_version", "selection"];
  if (policy === null || typeof policy !== "object" || Array.isArray(policy)) {
    fail("policy must be an object");
  }
  if (Object.keys(policy).sort().join("\n") !== expectedKeys.sort().join("\n")) {
    fail("policy fields differ from the supported schema");
  }
  if (policy.schema_version !== 1 || policy.name !== "base-learner-view") {
    fail("unsupported policy identity");
  }
  if (policy.selection !== "strict-top-level-allowlist") {
    fail("selection must be strict-top-level-allowlist");
  }
  if (Object.keys(policy.include ?? {}).sort().join("\n") !== "directories\nfiles") {
    fail("include fields differ from the supported schema");
  }
  if (Object.keys(policy.exclude ?? {}).sort().join("\n") !== "path_components\ntop_level") {
    fail("exclude fields differ from the supported schema");
  }
  assertStringArray(policy.include.files, "include.files");
  assertStringArray(policy.include.directories, "include.directories");
  assertStringArray(policy.exclude.top_level, "exclude.top_level");
  assertStringArray(policy.exclude.path_components, "exclude.path_components");

  const expectedFiles = [
    "README.md",
    "AGENTS.md",
    "MANIFEST.yaml",
    "REQUIREMENTS.md",
    "CONCEPTS.md",
    "DESIGN_QUESTIONS.md",
  ];
  const expectedDirectories = ["starter", "public_tests", "environment"];
  const expectedExcludedTopLevel = [
    "PROVENANCE.json",
    "LICENSE_BOUNDARY.md",
    "VALIDATION.md",
    "sealed",
    "adversarial",
    "benchmarks",
    "debugging",
    "review_exercises",
  ];
  const expectedExcludedComponents = [
    "sealed",
    "reference",
    "reference_tests",
    "hidden_tests",
    "solution",
    "solutions",
    "answers",
  ];
  if (JSON.stringify(policy.include.files) !== JSON.stringify(expectedFiles)) {
    fail("include.files differs from the baseline learner contract");
  }
  if (JSON.stringify(policy.include.directories) !== JSON.stringify(expectedDirectories)) {
    fail("include.directories differs from the baseline learner contract");
  }
  if (JSON.stringify(policy.exclude.top_level) !== JSON.stringify(expectedExcludedTopLevel)) {
    fail("exclude.top_level differs from the production-pack boundary");
  }
  if (JSON.stringify(policy.exclude.path_components) !== JSON.stringify(expectedExcludedComponents)) {
    fail("exclude.path_components differs from the production-pack boundary");
  }

  const included = new Set([...policy.include.files, ...policy.include.directories]);
  for (const entry of policy.exclude.top_level) {
    if (included.has(entry)) fail(`top-level path is both included and excluded: ${entry}`);
  }
  if (!policy.exclude.path_components.includes("sealed")) {
    fail("the sealed path component must always be excluded");
  }
  return policy;
}

function splitArchivePath(path) {
  if (
    typeof path !== "string"
    || path.length === 0
    || isAbsolute(path)
    || path.includes("\\")
    || /[\u0000-\u001f\u007f]/u.test(path)
  ) {
    fail(`invalid archive path: ${JSON.stringify(path)}`);
  }
  const components = path.split("/");
  if (components.some((component) => component === "" || component === "." || component === "..")) {
    fail(`non-canonical archive path: ${JSON.stringify(path)}`);
  }
  return components;
}

export function classifyPath(path, policy) {
  validatePolicy(policy);
  const components = splitArchivePath(path);
  const [topLevel] = components;
  if (policy.exclude.path_components.some((blocked) => components.includes(blocked))) {
    return "excluded-component";
  }
  if (policy.include.files.includes(topLevel)) {
    return components.length === 1 ? "learner" : "invalid-child-of-file";
  }
  if (policy.include.directories.includes(topLevel)) return "learner";
  if (policy.exclude.top_level.includes(topLevel)) return "instructor-only";
  return "unknown-top-level";
}

async function statusOrNull(path) {
  try {
    return await lstat(path);
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

function archiveRelative(root, path) {
  return relative(root, path).split(sep).join("/");
}

async function walkRegularFiles(
  root,
  directory,
  output,
  failures,
  { ignoreHostEntries = false, directories = null } = {},
) {
  const entries = await readdir(directory, { withFileTypes: true });
  entries.sort((left, right) => left.name.localeCompare(right.name, "en"));
  for (const entry of entries) {
    if (ignoreHostEntries && directory === root && hostOwnedTopLevel.has(entry.name)) continue;
    const path = join(directory, entry.name);
    const relativePath = archiveRelative(root, path);
    if (entry.isSymbolicLink()) failures.push(`symbolic link is not allowed: ${relativePath}`);
    else if (entry.isDirectory()) {
      if (directories !== null) directories.push(relativePath);
      await walkRegularFiles(root, path, output, failures, { ignoreHostEntries, directories });
    }
    else if (entry.isFile()) output.push(relativePath);
    else failures.push(`special file is not allowed: ${relativePath}`);
  }
}

async function hashFile(path) {
  return createHash("sha256").update(await readFile(path)).digest("hex");
}

function hashInventory(inventory) {
  const serialized = inventory.map(({ path, sha256 }) => `${sha256}  ${path}`).join("\n") + "\n";
  return createHash("sha256").update(serialized).digest("hex");
}

function extractStaticModuleSpecifiers(source) {
  const specifiers = [];
  const fromPattern = /(?:^|\n)\s*(?:import|export)\s+[\s\S]*?\sfrom\s+["']([^"'\n]+)["']\s*;/gu;
  const sideEffectPattern = /(?:^|\n)\s*import\s+["']([^"'\n]+)["']\s*;/gu;
  for (const pattern of [fromPattern, sideEffectPattern]) {
    for (const match of source.matchAll(pattern)) specifiers.push(match[1]);
  }
  return specifiers;
}

export async function auditSourceProjection(root = packRoot) {
  const policy = validatePolicy(JSON.parse(await readFile(join(root, policyPath), "utf8")));
  const failures = [];

  for (const file of policy.include.files) {
    const status = await statusOrNull(join(root, file));
    if (status === null || !status.isFile()) failures.push(`included regular file missing: ${file}`);
  }
  for (const directory of policy.include.directories) {
    const status = await statusOrNull(join(root, directory));
    if (status === null || !status.isDirectory()) failures.push(`included directory missing: ${directory}`);
  }
  for (const excluded of policy.exclude.top_level) {
    if ((await statusOrNull(join(root, excluded))) === null) {
      failures.push(`declared instructor-only top-level path missing: ${excluded}`);
    }
  }

  const sourceFiles = [];
  const sourceDirectories = [];
  await walkRegularFiles(root, root, sourceFiles, failures, {
    ignoreHostEntries: true,
    directories: sourceDirectories,
  });
  const learnerPaths = [];
  const learnerDirectories = [];
  let instructorFilesExcluded = 0;
  for (const path of sourceFiles) {
    const classification = classifyPath(path, policy);
    if (classification === "learner") learnerPaths.push(path);
    else if (classification === "instructor-only" || classification === "excluded-component") {
      instructorFilesExcluded += 1;
    } else {
      failures.push(`${classification}: ${path}`);
    }
  }
  for (const path of sourceDirectories) {
    const classification = classifyPath(path, policy);
    if (classification === "learner") learnerDirectories.push(path);
    else if (classification !== "instructor-only" && classification !== "excluded-component") {
      failures.push(`${classification}: ${path}`);
    }
  }
  learnerPaths.sort();
  learnerDirectories.sort();

  const inventory = await Promise.all(
    learnerPaths.map(async (path) => ({ path, sha256: await hashFile(join(root, path)) })),
  );
  if (inventory.some(({ path }) => splitArchivePath(path).some(
    (component) => policy.exclude.path_components.includes(component),
  ))) {
    failures.push("learner inventory contains an excluded path component");
  }
  const learnerPathSet = new Set(learnerPaths);
  let learnerModuleSpecifiers = 0;
  for (const path of learnerPaths.filter((candidate) => candidate.endsWith(".mjs"))) {
    const source = await readFile(join(root, path), "utf8");
    if (/\bimport\s*\(/u.test(source)) failures.push(`dynamic import is not allowed in learner view: ${path}`);
    for (const specifier of extractStaticModuleSpecifiers(source)) {
      learnerModuleSpecifiers += 1;
      if (specifier.startsWith("node:")) continue;
      if (!specifier.startsWith("./") && !specifier.startsWith("../")) {
        failures.push(`non-built-in module import in learner view: ${path} -> ${specifier}`);
        continue;
      }
      const target = posix.normalize(posix.join(posix.dirname(path), specifier));
      if (!learnerPathSet.has(target)) {
        failures.push(`module import escapes learner inventory: ${path} -> ${specifier}`);
      }
    }
  }
  if (failures.length > 0) fail(failures.join("; "));

  return {
    status: "PASS",
    mode: "source-projection-inventory",
    policy: policy.name,
    selection: policy.selection,
    learnerDirectories,
    learnerDirectoryCount: learnerDirectories.length,
    learnerFiles: inventory,
    learnerFileCount: inventory.length,
    learnerInventorySha256: hashInventory(inventory),
    instructorFilesExcluded,
    excludedPathComponentMatches: 0,
    learnerModuleSpecifiers,
    learnerImportEscapes: 0,
  };
}

export async function verifyMaterializedProjection(projectedRoot, root = packRoot) {
  const expected = await auditSourceProjection(root);
  const failures = [];
  const projectedStatus = await statusOrNull(projectedRoot);
  if (projectedStatus === null || !projectedStatus.isDirectory()) {
    fail("materialized projection root must be an existing real directory");
  }
  const actualPaths = [];
  const actualDirectories = [];
  await walkRegularFiles(projectedRoot, projectedRoot, actualPaths, failures, {
    directories: actualDirectories,
  });
  actualPaths.sort();
  actualDirectories.sort();
  const actual = await Promise.all(
    actualPaths.map(async (path) => ({ path, sha256: await hashFile(join(projectedRoot, path)) })),
  );
  if (JSON.stringify(actual) !== JSON.stringify(expected.learnerFiles)) {
    failures.push("materialized file paths or content hashes differ from the source projection inventory");
  }
  if (JSON.stringify(actualDirectories) !== JSON.stringify(expected.learnerDirectories)) {
    failures.push("materialized directory paths differ from the source projection inventory");
  }
  if (failures.length > 0) fail(failures.join("; "));
  return {
    status: "PASS",
    mode: "materialized-projection-verification",
    learnerDirectoryCount: actualDirectories.length,
    learnerFileCount: actual.length,
    learnerInventorySha256: hashInventory(actual),
    excludedPathComponentMatches: 0,
  };
}

async function main() {
  const arguments_ = process.argv.slice(2);
  let result;
  if (arguments_.length === 0) result = await auditSourceProjection(packRoot);
  else if (arguments_.length === 2 && arguments_[0] === "--projected-root") {
    result = await verifyMaterializedProjection(arguments_[1], packRoot);
  } else {
    throw new Error("usage: node environment/verify-learner-view.mjs [--projected-root PATH]");
  }
  console.log(JSON.stringify(result, null, 2));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
