"use strict";

function match(pattern, pathname) {
  const expected = pattern.split("/");
  const actual = pathname.split("/");
  if (expected.length !== actual.length) return null;

  const params = {};
  for (let index = 0; index < expected.length; index += 1) {
    if (expected[index].startsWith(":")) {
      params[expected[index].slice(1)] = decodeURIComponent(actual[index]);
    } else if (expected[index] !== actual[index]) {
      return null;
    }
  }
  return params;
}

class Router {
  constructor() {
    this.layers = [];
    this.sharedParams = {};
  }

  use(prefix, handler) {
    this.layers.push({ kind: "mount", prefix, handler });
  }

  get(pattern, handler) {
    this.layers.push({ kind: "route", method: "GET", pattern, handler });
  }

  async handle(req, res) {
    const pathname = new URL(req.url, "http://local.invalid").pathname;

    for (const layer of this.layers) {
      if (layer.kind === "mount" && pathname.startsWith(layer.prefix)) {
        layer.handler(req, res);
        continue;
      }

      if (layer.kind === "route" && req.method === layer.method) {
        const params = match(layer.pattern, pathname);
        if (params) {
          Object.assign(this.sharedParams, params);
          req.params = this.sharedParams;
          await layer.handler(req, res);
          return;
        }
      }
    }

    res.statusCode = 404;
    res.end("Not Found");
  }
}

module.exports = { Router };
