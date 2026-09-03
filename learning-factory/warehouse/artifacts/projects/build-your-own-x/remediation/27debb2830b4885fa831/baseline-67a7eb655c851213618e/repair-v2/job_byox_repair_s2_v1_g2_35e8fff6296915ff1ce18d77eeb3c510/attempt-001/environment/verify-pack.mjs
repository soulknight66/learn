import { createHash } from "node:crypto";
import { lstat, readFile, readdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { auditSourceProjection } from "./verify-learner-view.mjs";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const required = [
  "README.md",
  "AGENTS.md",
  "MANIFEST.yaml",
  "PROVENANCE.json",
  "LICENSE_BOUNDARY.md",
  "REQUIREMENTS.md",
  "CONCEPTS.md",
  "DESIGN_QUESTIONS.md",
  "VALIDATION.md",
  "starter/README.md",
  "public_tests/README.md",
  "environment/README.md",
  "sealed/reference/README.md",
  "sealed/reference_tests/README.md",
  "sealed/DESIGN.md",
  "sealed/TRADEOFFS.md",
  "sealed/REVIEW.md",
  "sealed/alternatives/README.md",
  "sealed/production/PRODUCTIONIZATION.md",
  "adversarial/README.md",
  "debugging/README.md",
  "review_exercises/README.md",
  "benchmarks/README.md",
];
const forbidden = [
  ".git", ".env", ".venv", "credentials.json", "secrets", "reference", "reference_tests",
  "hidden_tests", "solution", "solutions", "answers", "starter/sealed", "starter/reference",
  "starter/reference_tests", "starter/solution", "starter/solutions", "starter/answers",
  "public_tests/sealed", "public_tests/reference", "public_tests/hidden_tests",
  "environment/sealed",
];
const expectedManifest = {
  independent_validation: "REQUIRED",
  productionized: false,
  project_id: "project_c305a6b70f268e23e2e48694e3604f28",
  provenance_sha256: "d786b92f24430d9ac930aa10c1a53211415cbcbdc115c85abc385026f71fd048",
  schema_version: 1,
  source_commit: "aa17439b62f384511a5561ce308e9598b94d8989",
  source_id: "source_eac489a34bed5db9a1f2a580b457bcef",
  status: "GENERATED",
  validation_labels: ["GENERATED", "PARTIAL"],
};
const expectedProvenanceFileSha256 = "be80da9777a7b3f1b6a4d2d40a2f3cde0f9212467b828a636140bc281ff94bdc";

const failures = [];
let fileCount = 0;
const filePaths = [];
const hostOwnedRootEntries = new Set([
  ".agents",
  ".codex",
  ".factory-workspace",
  "PRIOR_BUILD",
  "PRIOR_REVIEW",
]);
const canonicalTopLevel = new Map([
  ["AGENTS.md", "file"],
  ["CONCEPTS.md", "file"],
  ["DESIGN_QUESTIONS.md", "file"],
  ["LICENSE_BOUNDARY.md", "file"],
  ["MANIFEST.yaml", "file"],
  ["PROVENANCE.json", "file"],
  ["README.md", "file"],
  ["REQUIREMENTS.md", "file"],
  ["VALIDATION.md", "file"],
  ["adversarial", "directory"],
  ["benchmarks", "directory"],
  ["debugging", "directory"],
  ["environment", "directory"],
  ["public_tests", "directory"],
  ["review_exercises", "directory"],
  ["sealed", "directory"],
  ["starter", "directory"],
]);

async function statOrNull(path) {
  try {
    return await lstat(path);
  } catch (error) {
    if (error?.code === "ENOENT") return null;
    throw error;
  }
}

for (const relative of required) {
  const status = await statOrNull(join(root, relative));
  if (status === null || !status.isFile()) failures.push(`required regular file missing: ${relative}`);
}
for (const relative of forbidden) {
  if ((await statOrNull(join(root, relative))) !== null) failures.push(`forbidden path exists: ${relative}`);
}

for (const entry of await readdir(root, { withFileTypes: true })) {
  if (hostOwnedRootEntries.has(entry.name)) continue;
  const expectedKind = canonicalTopLevel.get(entry.name);
  if (expectedKind === undefined) failures.push(`unexpected top-level path: ${entry.name}`);
  else if (expectedKind === "file" && !entry.isFile()) failures.push(`top-level file has wrong kind: ${entry.name}`);
  else if (expectedKind === "directory" && !entry.isDirectory()) {
    failures.push(`top-level directory has wrong kind: ${entry.name}`);
  }
}

async function walk(directory, relative = "") {
  const entries = await readdir(directory, { withFileTypes: true });
  for (const entry of entries) {
    if (relative === "" && hostOwnedRootEntries.has(entry.name)) continue;
    const childRelative = relative === "" ? entry.name : join(relative, entry.name);
    const child = join(directory, entry.name);
    if (entry.isSymbolicLink()) failures.push(`symlink is not archivable: ${childRelative}`);
    else if (entry.isDirectory()) await walk(child, childRelative);
    else if (entry.isFile()) {
      fileCount += 1;
      filePaths.push(childRelative);
    } else failures.push(`special file is not archivable: ${childRelative}`);
  }
}
await walk(root);

const manifest = JSON.parse(await readFile(join(root, "MANIFEST.yaml"), "utf8"));
if (JSON.stringify(manifest) !== JSON.stringify(expectedManifest)) failures.push("manifest object differs");

const provenanceText = await readFile(join(root, "PROVENANCE.json"), "utf8");
const provenanceFileSha256 = createHash("sha256").update(provenanceText).digest("hex");
if (provenanceFileSha256 !== expectedProvenanceFileSha256) {
  failures.push("provenance object differs from the immutable snapshot");
}
const provenance = JSON.parse(provenanceText);
if (provenance.snapshot_sha256 !== expectedManifest.provenance_sha256) {
  failures.push("provenance snapshot does not match manifest");
}
if (provenance.project?.project_id !== expectedManifest.project_id) {
  failures.push("provenance project does not match manifest");
}
if (provenance.license_boundary?.linked_content_copied !== false) {
  failures.push("provenance does not preserve the no-copy boundary");
}

let learnerProjection = null;
try {
  learnerProjection = await auditSourceProjection(root);
} catch (error) {
  failures.push(error.message);
}

const credentialPatterns = [
  ["private key block", new RegExp(["-----BEGIN ", "(?:RSA |EC |OPENSSH )?", "PRIVATE KEY-----"].join(""))],
  ["AWS access key", new RegExp("\\bA" + "KIA[0-9A-Z]{16}\\b")],
  ["GitHub token", new RegExp("\\b(?:g" + "hp|github_pat)_[A-Za-z0-9_]{20,}\\b")],
  ["OpenAI-style token", new RegExp("\\bs" + "k-[A-Za-z0-9]{20,}\\b")],
  ["assigned secret", /(?:password|passwd|api[_-]?key)\s*[:=]\s*["'][^"'\n]{8,}["']/i],
];
for (const relative of filePaths) {
  const content = await readFile(join(root, relative), "utf8");
  for (const [label, pattern] of credentialPatterns) {
    if (pattern.test(content)) failures.push(`${label} pattern in ${relative}`);
  }
}

if (failures.length > 0) {
  console.error(JSON.stringify({ status: "FAIL", failures }, null, 2));
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({
    status: "PASS",
    requiredRegularFiles: required.length,
    forbiddenPathsPresent: 0,
    symlinksOrSpecialFiles: 0,
    credentialPatternMatches: 0,
    scannedFiles: fileCount,
    manifestStatus: manifest.status,
    validationLabels: manifest.validation_labels,
    learnerProjectionStatus: learnerProjection.status,
    learnerFileCount: learnerProjection.learnerFileCount,
    learnerInventorySha256: learnerProjection.learnerInventorySha256,
    learnerImportEscapes: learnerProjection.learnerImportEscapes,
  }, null, 2));
}
