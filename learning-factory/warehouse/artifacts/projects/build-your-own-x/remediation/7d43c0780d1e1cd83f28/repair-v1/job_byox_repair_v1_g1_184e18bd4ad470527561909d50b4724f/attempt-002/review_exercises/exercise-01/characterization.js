"use strict";

const assert = require("node:assert/strict");
const { Router } = require("./flawed-router");

function response() {
  return {
    statusCode: 200,
    body: "",
    end(value = "") {
      this.body += String(value);
    },
  };
}

(async () => {
  const router = new Router();
  let mountHits = 0;
  router.use("/api", () => {
    mountHits += 1;
  });

  let releaseFirst;
  const firstCanFinish = new Promise((resolve) => {
    releaseFirst = resolve;
  });
  router.get("/users/:id", async (req, res) => {
    if (req.params.id === "first") await firstCanFinish;
    res.end(req.params.id);
  });

  await router.handle({ method: "GET", url: "/apiary" }, response());

  const firstResponse = response();
  const secondResponse = response();
  const first = router.handle({ method: "GET", url: "/users/first" }, firstResponse);
  const second = router.handle({ method: "GET", url: "/users/second" }, secondResponse);
  await second;
  releaseFirst();
  await first;

  let malformed;
  try {
    const malformedResponse = response();
    await router.handle({ method: "GET", url: "/users/%ZZ" }, malformedResponse);
    malformed = String(malformedResponse.statusCode);
  } catch (error) {
    malformed = error.name;
  }

  const observed = {
    mountHits,
    concurrentBodies: [firstResponse.body, secondResponse.body],
    malformed,
  };
  const intended = {
    mountHits: 0,
    concurrentBodies: ["first", "second"],
    malformed: "500",
  };

  try {
    assert.deepEqual(observed, intended);
    process.stdout.write("PASS router observations satisfy the proposed contract\n");
  } catch (error) {
    process.stderr.write(`REVIEW NEEDED\nobserved: ${JSON.stringify(observed)}\n`);
    process.stderr.write(`intended: ${JSON.stringify(intended)}\n`);
    process.exitCode = 1;
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
