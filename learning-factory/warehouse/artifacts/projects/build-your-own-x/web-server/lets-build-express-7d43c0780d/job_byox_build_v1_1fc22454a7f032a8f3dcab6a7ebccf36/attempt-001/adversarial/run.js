"use strict";

const assert = require("node:assert/strict");
const http = require("node:http");
const path = require("node:path");

const REQUEST_DEADLINE_MS = 2000;
const CLOSE_DEADLINE_MS = 1000;
const MAX_RESPONSE_BYTES = 1024 * 1024;

const target = process.argv[2]
  ? path.resolve(process.cwd(), process.argv[2])
  : path.join(__dirname, "..", "sealed", "reference", "src", "index.js");

function loadFactory(filename) {
  // The target is chosen by the local instructor running this harness.
  // eslint-disable-next-line global-require, import/no-dynamic-require
  const implementation = require(filename);
  assert.equal(
    typeof implementation,
    "function",
    `${filename} must export createApplication directly`,
  );
  return implementation;
}

const createApplication = loadFactory(target);

function listen(server) {
  return new Promise((resolve, reject) => {
    const onError = (error) => {
      server.off("listening", onListening);
      reject(error);
    };
    const onListening = () => {
      server.off("error", onError);
      resolve(server.address());
    };
    server.once("error", onError);
    server.once("listening", onListening);
    server.listen(0, "127.0.0.1");
  });
}

function close(server, sockets) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      clearTimeout(deadline);
      resolve();
    };
    const deadline = setTimeout(finish, CLOSE_DEADLINE_MS);
    server.close(finish);
    if (typeof server.closeAllConnections === "function") {
      server.closeAllConnections();
    }
    for (const socket of sockets) socket.destroy();
  });
}

function request(port, options = {}) {
  return new Promise((resolve, reject) => {
    let settled = false;
    let req;
    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(deadline);
      callback(value);
    };
    const fail = (error) => {
      if (settled) return;
      if (req && !req.destroyed) req.destroy();
      finish(reject, error);
    };
    const deadline = setTimeout(() => {
      fail(new Error(`request exceeded the ${REQUEST_DEADLINE_MS}ms absolute deadline`));
    }, REQUEST_DEADLINE_MS);

    req = http.request(
      {
        host: "127.0.0.1",
        port,
        method: options.method || "GET",
        path: options.path || "/",
        headers: options.headers || {},
        agent: false,
      },
      (res) => {
        const chunks = [];
        let byteLength = 0;
        res.on("data", (chunk) => {
          byteLength += chunk.length;
          if (byteLength > MAX_RESPONSE_BYTES) {
            const error = new Error(`response exceeded ${MAX_RESPONSE_BYTES} bytes`);
            res.destroy(error);
            fail(error);
            return;
          }
          chunks.push(chunk);
        });
        res.on("aborted", () => fail(new Error("response aborted before completion")));
        res.on("error", fail);
        res.on("end", () => {
          finish(resolve, {
            status: res.statusCode,
            headers: res.headers,
            body: Buffer.concat(chunks),
          });
        });
      },
    );

    req.on("error", fail);
    if (options.body !== undefined) {
      req.write(options.body);
    }
    req.end();
  });
}

async function withApplication(configure, exercise) {
  const app = createApplication();
  assert.equal(typeof app, "function", "createApplication() must return a request listener");
  configure(app);

  const server = http.createServer(app);
  const sockets = new Set();
  server.on("connection", (socket) => {
    sockets.add(socket);
    socket.on("close", () => sockets.delete(socket));
  });

  const address = await listen(server);
  try {
    await exercise(address.port);
  } finally {
    await close(server, sockets);
  }
}

function json(response) {
  return JSON.parse(response.body.toString("utf8"));
}

const tests = [
  [
    "ordered mounts, params, and duplicate query keys",
    async () => {
      const order = [];
      await withApplication(
        (app) => {
          app.use((req, res, next) => {
            order.push("root");
            next();
          });
          app.use("/api", (req, res, next) => {
            order.push("api");
            next();
          });
          app.get("/api/users/:id", (req, res) => {
            res.status(201).set("x-order", order.join(",")).json({
              originalUrl: req.originalUrl,
              path: req.path,
              id: req.params.id,
              paramsArePlain: Object.getPrototypeOf(req.params) === Object.prototype,
              queryIsPlain: Object.getPrototypeOf(req.query) === Object.prototype,
              tags: req.query.tag,
              shadowName: req.query.toString,
              specialName: req.query.__proto__,
              specialNameIsOwn: Object.prototype.hasOwnProperty.call(req.query, "__proto__"),
              constructorName: req.query.constructor,
            });
          });
        },
        async (port) => {
          const response = await request(port, {
            path: "/api/users/a%20b?tag=one&tag=two&toString=value&__proto__=data&constructor=ctor",
          });
          assert.equal(response.status, 201);
          assert.equal(response.headers["x-order"], "root,api");
          assert.deepEqual(json(response), {
            originalUrl: "/api/users/a%20b?tag=one&tag=two&toString=value&__proto__=data&constructor=ctor",
            path: "/api/users/a%20b",
            id: "a b",
            paramsArePlain: true,
            queryIsPlain: true,
            tags: ["one", "two"],
            shadowName: "value",
            specialName: "data",
            specialNameIsOwn: true,
            constructorName: "ctor",
          });
        },
      );
    },
  ],
  [
    "mounted middleware observes segment boundaries",
    async () => {
      let apiHits = 0;
      await withApplication(
        (app) => {
          app.use("/api", (req, res, next) => {
            apiHits += 1;
            next();
          });
          app.use((req, res) => res.json({ apiHits }));
        },
        async (port) => {
          assert.deepEqual(json(await request(port, { path: "/apiary" })), { apiHits: 0 });
          assert.deepEqual(json(await request(port, { path: "/api/users" })), { apiHits: 1 });
        },
      );
    },
  ],
  [
    "a final wildcard captures and decodes the remaining path",
    async () => {
      await withApplication(
        (app) => {
          app.get("/files/*", (req, res) => {
            res.json({
              capture: req.params[0],
              plainObject: Object.getPrototypeOf(req.params) === Object.prototype,
            });
          });
          app.get("/special/:__proto__/:constructor", (req, res) => {
            res.json({
              prototypeIntact: Object.getPrototypeOf(req.params) === Object.prototype,
              specialName: req.params.__proto__,
              specialNameIsOwn: Object.prototype.hasOwnProperty.call(req.params, "__proto__"),
              constructorName: req.params.constructor,
              constructorNameIsOwn: Object.prototype.hasOwnProperty.call(req.params, "constructor"),
            });
          });
        },
        async (port) => {
          const response = await request(port, { path: "/files/a%20b/c.txt" });
          assert.equal(response.status, 200);
          assert.deepEqual(json(response), { capture: "a b/c.txt", plainObject: true });

          const special = await request(port, { path: "/special/proto-value/constructor-value" });
          assert.deepEqual(json(special), {
            prototypeIntact: true,
            specialName: "proto-value",
            specialNameIsOwn: true,
            constructorName: "constructor-value",
            constructorNameIsOwn: true,
          });
        },
      );
    },
  ],
  [
    "HEAD routing is separate from GET routing",
    async () => {
      await withApplication(
        (app) => {
          app.get("/explicit", (req, res) => res.set("x-selected", "get").send("get body"));
          app.head("/explicit", (req, res) => res.set("x-selected", "head").send("head body"));
          app.get("/fallback", (req, res) => res.set("x-selected", "get").send("fallback body"));
        },
        async (port) => {
          const explicit = await request(port, { method: "HEAD", path: "/explicit" });
          assert.equal(explicit.status, 200);
          assert.equal(explicit.headers["x-selected"], "head");
          assert.equal(explicit.body.length, 0);

          const fallback = await request(port, { method: "HEAD", path: "/fallback" });
          assert.equal(fallback.status, 404);
          assert.equal(fallback.headers["x-selected"], undefined);
          assert.equal(fallback.body.length, 0);
        },
      );
    },
  ],
  [
    "every non-null, non-undefined next argument enters error mode",
    async () => {
      await withApplication(
        (app) => {
          app.get("/false", (req, res, next) => next(false));
          app.get("/zero", (req, res, next) => next(0));
          app.get("/empty", (req, res, next) => next(""));
          app.use((error, req, res, next) => {
            void req;
            void next;
            res.status(409).send(`${typeof error}:${String(error)}`);
          });
        },
        async (port) => {
          for (const [pathname, body] of [
            ["/false", "boolean:false"],
            ["/zero", "number:0"],
            ["/empty", "string:"],
          ]) {
            const response = await request(port, { path: pathname });
            assert.equal(response.status, 409);
            assert.equal(response.body.toString("utf8"), body);
          }
        },
      );
    },
  ],
  [
    "next(error), throws, and rejected promises enter error mode",
    async () => {
      await withApplication(
        (app) => {
          app.get("/next", (req, res, next) => next(new Error("from next")));
          app.get("/throw", () => {
            throw new Error("from throw");
          });
          app.get("/reject", async () => {
            throw new Error("from rejection");
          });
          app.use((error, req, res, next) => {
            void next;
            res.status(503).json({ message: error.message });
          });
        },
        async (port) => {
          for (const [pathname, message] of [
            ["/next", "from next"],
            ["/throw", "from throw"],
            ["/reject", "from rejection"],
          ]) {
            const response = await request(port, { path: pathname });
            assert.equal(response.status, 503);
            assert.deepEqual(json(response), { message });
          }
        },
      );
    },
  ],
  [
    "a handler's repeated next call is ignored",
    async () => {
      let lateErrors = 0;
      await withApplication(
        (app) => {
          app.get(
            "/once",
            (req, res, next) => {
              next();
              next(new Error("late"));
            },
            (req, res) => res.send("ok"),
          );
          app.get("/error-count", (req, res) => res.json({ lateErrors }));
          app.use((error, req, res, next) => {
            void error;
            void req;
            void next;
            lateErrors += 1;
            if (!res.writableEnded) {
              res.status(500).send("unexpected late error");
            }
          });
        },
        async (port) => {
          const first = await request(port, { path: "/once" });
          assert.equal(first.status, 200);
          assert.equal(first.body.toString("utf8"), "ok");
          assert.deepEqual(json(await request(port, { path: "/error-count" })), { lateErrors: 0 });
        },
      );
    },
  ],
  [
    "malformed capture escapes enter error middleware without poisoning the server",
    async () => {
      await withApplication(
        (app) => {
          app.get("/items/:id", (req, res) => res.send(req.params.id));
          app.use((error, req, res, next) => {
            void req;
            void next;
            res.status(422).json({ name: error && error.name });
          });
        },
        async (port) => {
          const malformed = await request(port, { path: "/items/%ZZ" });
          assert.equal(malformed.status, 422);
          assert.deepEqual(json(malformed), { name: "URIError" });

          const healthy = await request(port, { path: "/items/healthy" });
          assert.equal(healthy.status, 200);
          assert.equal(healthy.body.toString("utf8"), "healthy");
        },
      );
    },
  ],
  [
    "request params remain isolated while handlers overlap",
    async () => {
      let arrivals = 0;
      let releaseBarrier;
      const bothHandlersArrived = new Promise((resolve) => {
        releaseBarrier = resolve;
      });
      await withApplication(
        (app) => {
          app.get("/slow/:id", async (req, res) => {
            arrivals += 1;
            if (arrivals === 2) releaseBarrier();
            await bothHandlersArrived;
            res.json({ id: req.params.id, plainObject: Object.getPrototypeOf(req.params) === Object.prototype });
          });
        },
        async (port) => {
          const [first, second] = await Promise.all([
            request(port, { path: "/slow/first" }),
            request(port, { path: "/slow/second" }),
          ]);
          assert.deepEqual(json(first), { id: "first", plainObject: true });
          assert.deepEqual(json(second), { id: "second", plainObject: true });
        },
      );
    },
  ],
  [
    "unhandled normal and error flows receive deterministic defaults",
    async () => {
      await withApplication(
        (app) => {
          app.get("/explode", () => {
            throw new Error("private detail must not leak");
          });
        },
        async (port) => {
          const missing = await request(port, { path: "/missing" });
          assert.equal(missing.status, 404);
          assert.equal(missing.headers["content-type"], "text/plain; charset=utf-8");
          assert.equal(missing.headers["content-length"], String(Buffer.byteLength("Not Found")));
          assert.equal(missing.body.toString("utf8"), "Not Found");

          const exploded = await request(port, { path: "/explode" });
          assert.equal(exploded.status, 500);
          assert.equal(exploded.headers["content-type"], "text/plain; charset=utf-8");
          assert.equal(exploded.headers["content-length"], String(Buffer.byteLength("Internal Server Error")));
          assert.equal(exploded.body.toString("utf8"), "Internal Server Error");

          const headMissing = await request(port, { method: "HEAD", path: "/missing" });
          assert.equal(headMissing.status, 404);
          assert.equal(headMissing.headers["content-length"], String(Buffer.byteLength("Not Found")));
          assert.equal(headMissing.body.length, 0);
        },
      );
    },
  ],
];

(async () => {
  let failures = 0;
  for (const [name, test] of tests) {
    try {
      await test();
      process.stdout.write(`PASS ${name}\n`);
    } catch (error) {
      failures += 1;
      process.stderr.write(`FAIL ${name}\n${error.stack || error}\n`);
    }
  }

  process.stdout.write(`${tests.length - failures}/${tests.length} adversarial checks passed\n`);
  if (failures > 0) {
    process.exitCode = 1;
  }
})().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
