'use strict';

const http = require('node:http');
const { compose } = require('./compose');
const { HttpError } = require('./http-error');
const { Router, methodMatches } = require('./router');
const { decorateResponse } = require('./response');

const ROUTE_METHODS = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options'];
const ERROR_RESPONSE_HEADERS_TO_CLEAR = Object.freeze([
  'connection',
  'content-encoding',
  'content-length',
  'content-range',
  'content-type',
  'trailer',
  'transfer-encoding'
]);
const SAFE_ERROR_HEADERS = new Set([
  'allow',
  'proxy-authenticate',
  'retry-after',
  'www-authenticate'
]);

function normalizePrefix(prefix) {
  if (typeof prefix !== 'string' || !prefix.startsWith('/')) {
    throw new TypeError('middleware prefix must be a string beginning with /');
  }
  if (prefix.includes('?') || prefix.includes('#')) {
    throw new TypeError('middleware prefix must not include a query or fragment');
  }
  while (prefix.length > 1 && prefix.endsWith('/')) {
    prefix = prefix.slice(0, -1);
  }
  return prefix;
}

function prefixMatches(prefix, pathname) {
  return prefix === '/'
    || pathname === prefix
    || pathname.startsWith(`${prefix}/`);
}

function decorateRequest(req) {
  const target = typeof req.url === 'string' && req.url.length > 0 ? req.url : '/';
  let parsed;
  try {
    parsed = new URL(target, 'http://local.invalid');
    decodeURI(parsed.pathname);
  } catch (cause) {
    throw new HttpError(400, 'Malformed request target', {
      cause,
      code: 'MALFORMED_TARGET'
    });
  }

  req.originalUrl = target;
  req.path = parsed.pathname;
  req.query = parsed.searchParams;
  req.params = Object.create(null);
  delete req.routePattern;
}

function copySafeErrorHeaders(res, headers) {
  if (headers === null || typeof headers !== 'object') {
    return;
  }
  for (const [name, value] of Object.entries(headers)) {
    if (!SAFE_ERROR_HEADERS.has(name.toLowerCase())) {
      continue;
    }
    try {
      res.setHeader(name, value);
    } catch (_ignored) {
      // Invalid error metadata must not replace the original failure.
    }
  }
}

function clearErrorResponseHeaders(res) {
  for (const name of ERROR_RESPONSE_HEADERS_TO_CLEAR) {
    res.removeHeader(name);
  }
}

function errorDetails(error) {
  const candidate = error && (error.status || error.statusCode);
  const status = Number.isInteger(candidate) && candidate >= 400 && candidate <= 599
    ? candidate
    : 500;
  const exposed = Boolean(error && error.expose === true) || status < 500;
  const message = exposed && error && typeof error.message === 'string'
    ? error.message
    : 'Internal Server Error';
  return { status, message };
}

function sendError(res, error) {
  if (res.headersSent) {
    res.destroy(error instanceof Error ? error : undefined);
    return;
  }

  const details = errorDetails(error);
  const body = Buffer.from(JSON.stringify({ error: details }), 'utf8');
  clearErrorResponseHeaders(res);
  res.statusCode = details.status;
  copySafeErrorHeaders(res, error && error.headers);
  res.setHeader('content-type', 'application/json; charset=utf-8');
  res.setHeader('content-length', String(body.length));
  res.end(body);
}

class Application {
  constructor() {
    this.layers = [];
    this.router = new Router();
    this.publicApplication = null;

    for (const method of ROUTE_METHODS) {
      this[method] = (pattern, ...handlers) => this.registerRoute(method, pattern, handlers);
    }
  }

  use(pathOrHandler, maybeHandler) {
    const hasPrefix = typeof pathOrHandler === 'string';
    const prefix = hasPrefix ? normalizePrefix(pathOrHandler) : null;
    const handler = hasPrefix ? maybeHandler : pathOrHandler;
    if (typeof handler !== 'function') {
      throw new TypeError('middleware must be a function');
    }

    this.layers.push(Object.freeze({
      type: 'middleware',
      prefix,
      handler
    }));
    return this.publicApplication;
  }

  registerRoute(method, pattern, handlers) {
    this.layers.push(this.router.createRoute(method.toUpperCase(), pattern, handlers));
    return this.publicApplication;
  }

  layerHandler(layer) {
    if (layer.type === 'middleware') {
      return (req, res, next) => {
        if (layer.prefix === null || prefixMatches(layer.prefix, req.path)) {
          return layer.handler(req, res, next);
        }
        return next();
      };
    }

    return async (req, res, next) => {
      if (!methodMatches(layer.method, req.method) || !this.router.pathMatches(layer, req.path)) {
        return next();
      }

      const parameters = this.router.match(layer, req.path);
      const previousParameters = req.params;
      const hadRoutePattern = Object.prototype.hasOwnProperty.call(req, 'routePattern');
      const previousRoutePattern = req.routePattern;
      req.params = parameters;
      req.routePattern = layer.compiled.pattern;

      try {
        const runRoute = compose(layer.handlers, next);
        return await runRoute(req, res);
      } finally {
        req.params = previousParameters;
        if (hadRoutePattern) {
          req.routePattern = previousRoutePattern;
        } else {
          delete req.routePattern;
        }
      }
    };
  }

  terminal(layers) {
    return (req, res) => {
      if (res.writableEnded || res.headersSent) {
        return;
      }

      const allowed = this.router.allowedMethods(layers, req.path);
      if (req.method === 'OPTIONS' && allowed.length > 0) {
        return res.status(204).set('allow', allowed.join(', ')).send();
      }
      if (allowed.length > 0 && !allowed.includes(req.method)) {
        return res
          .status(405)
          .set('allow', allowed.join(', '))
          .json({ error: { status: 405, message: 'Method Not Allowed' } });
      }
      return res.status(404).json({ error: { status: 404, message: 'Not Found' } });
    };
  }

  async handle(req, res) {
    try {
      req.method = String(req.method || 'GET').toUpperCase();
      decorateRequest(req);
      decorateResponse(res, req.method);

      const layers = this.layers.slice();
      const middleware = layers.map((layer) => this.layerHandler(layer));
      const run = compose(middleware, this.terminal(layers));
      await run(req, res);

      if (!res.writableEnded && !res.headersSent) {
        this.terminal(layers)(req, res);
      }
    } catch (error) {
      sendError(res, error);
    }
  }

  listen(...args) {
    const server = http.createServer((req, res) => {
      Promise.resolve(this.handle(req, res)).catch((error) => sendError(res, error));
    });
    server.listen(...args);
    return server;
  }
}

module.exports = {
  Application,
  ROUTE_METHODS,
  normalizePrefix,
  prefixMatches,
  decorateRequest,
  errorDetails,
  sendError
};
