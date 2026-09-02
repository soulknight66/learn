'use strict';

const http = require('node:http');
const { compose } = require('./compose');
const { Router } = require('./router');
const { decorateResponse } = require('./response');

const ROUTE_METHODS = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options'];

class Application {
  constructor() {
    this.layers = [];
    this.router = new Router();

    for (const method of ROUTE_METHODS) {
      this[method] = (pattern, ...handlers) => this.registerRoute(method, pattern, handlers);
    }
  }

  use(pathOrHandler, maybeHandler) {
    const path = typeof pathOrHandler === 'string' ? pathOrHandler : null;
    const handler = path === null ? pathOrHandler : maybeHandler;
    if (typeof handler !== 'function') {
      throw new TypeError('middleware must be a function');
    }
    this.layers.push({ type: 'middleware', path, handler });
    return this.publicApplication;
  }

  registerRoute(method, pattern, handlers) {
    if (handlers.length === 0 || handlers.some((handler) => typeof handler !== 'function')) {
      throw new TypeError('a route requires one or more handler functions');
    }
    this.layers.push(this.router.createRoute(method.toUpperCase(), pattern, handlers));
    return this.publicApplication;
  }

  async handle(req, res) {
    // TODO:
    // 1. decorate a fresh request and response,
    // 2. turn layers into a composed chain while preserving registration order,
    // 3. distinguish 404/405/OPTIONS at the terminal,
    // 4. translate pre-header errors and terminate post-header failures.
    decorateResponse(res, req.method);
    const run = compose([], undefined);
    return run(req, res);
  }

  listen(...args) {
    const server = http.createServer((req, res) => {
      Promise.resolve(this.handle(req, res)).catch(() => {
        if (!res.headersSent) {
          res.statusCode = 500;
          res.end();
        } else {
          res.destroy();
        }
      });
    });
    server.listen(...args);
    return server;
  }
}

module.exports = { Application, ROUTE_METHODS };
