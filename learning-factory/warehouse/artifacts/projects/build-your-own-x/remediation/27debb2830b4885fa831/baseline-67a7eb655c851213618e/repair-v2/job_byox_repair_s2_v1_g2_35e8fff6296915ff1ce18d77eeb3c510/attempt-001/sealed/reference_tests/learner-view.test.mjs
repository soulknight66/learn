import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  auditSourceProjection,
  classifyPath,
  validatePolicy,
  verifyMaterializedProjection,
} from "../../environment/verify-learner-view.mjs";

const policy = validatePolicy(JSON.parse(await readFile(
  new URL("../../environment/learner-view-policy.json", import.meta.url),
  "utf8",
)));

test("learner projection uses the baseline allowlist", () => {
  assert.equal(classifyPath("README.md", policy), "learner");
  assert.equal(classifyPath("starter/src/parser.mjs", policy), "learner");
  assert.equal(classifyPath("public_tests/parser.test.mjs", policy), "learner");
  assert.equal(classifyPath("sealed/reference/src/parser.mjs", policy), "excluded-component");
  assert.equal(classifyPath("debugging/01-scope-lifetime/README.md", policy), "instructor-only");
  assert.equal(
    classifyPath("debugging/01-scope-lifetime/sealed/ANSWER.md", policy),
    "excluded-component",
  );
});

test("learner projection rejects traversal and unknown roots", () => {
  assert.throws(() => classifyPath("starter/../sealed/REVIEW.md", policy), /non-canonical/);
  assert.equal(classifyPath("unexpected/file.mjs", policy), "unknown-top-level");
  assert.equal(classifyPath("starter/sealed/ANSWER.md", policy), "excluded-component");
});

test("source projection inventory contains no sealed component", async () => {
  const root = fileURLToPath(new URL("../../", import.meta.url));
  const result = await auditSourceProjection(root);
  assert.equal(result.status, "PASS");
  assert.ok(result.instructorFilesExcluded > 0);
  assert.equal(result.excludedPathComponentMatches, 0);
  assert.equal(result.learnerFiles.some(({ path }) => path.split("/").includes("sealed")), false);
  assert.equal(result.learnerFiles.some(({ path }) => path === "starter/example.mica"), true);
});

test("materialized verifier rejects an incomplete existing tree", async () => {
  const root = fileURLToPath(new URL("../../", import.meta.url));
  const starter = fileURLToPath(new URL("../../starter/", import.meta.url));
  await assert.rejects(
    () => verifyMaterializedProjection(starter, root),
    /materialized (?:file|directory) paths differ/,
  );
});
