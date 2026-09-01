'use strict';

const http = require('node:http');

const NO_ERROR = Symbol('no error');

const MIME_TYPES = Object.freeze({
  css: 'text/css; charset=utf-8',
  html: 'text/html; charset=utf-8',
  htm: 'text/html; charset=utf-8',
  js: 'text/javascript; charset=utf-8',
  json: 'application/json; charset=utf-8',
  text: 'text/plain; charset=utf-8',
  txt: 'text/plain; charset=utf-8',
  xml: 'application/xml; charset=utf-8',
});

function createDictionary() {
  return {};
}

function own(object, key) {
  return Object.prototype.hasOwnProperty.call(object, key);
}

function defineOwn(object, key, value) {
  Object.defineProperty(object, key, {
    value,
    writable: true,
    enumerable: true,
    configurable: true,
  });
}

function escapeRegularExpression(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function compileRoutePath(pattern) {
  if (typeof pattern !== 'string' || pattern.length === 0) {
    throw new TypeError('path must be a non-empty string');
  }
  if (pattern !== '*' && !pattern.startsWith('/')) {
    throw new TypeError('path must start with "/" or be "*"');
  }

  const keys = [];
  const names = new Set();
  let source;

  if (pattern === '*') {
    keys.push('0');
    source = '(.*)';
  } else {
    const segments = pattern.split('/');
    source = '';

    for (let index = 1; index < segments.length; index += 1) {
      const segment = segments[index];
      source += '/';

      if (segment === '*') {
        if (index !== segments.length - 1) {
          throw new TypeError('wildcard must be the final path segment');
        }
        keys.push('0');
        source += '(.*)';
        continue;
      }

      if (segment.includes('*')) {
        throw new TypeError('wildcard must be an entire final path segment');
      }

      if (segment.startsWith(':')) {
        const match = /^:([A-Za-z_][A-Za-z0-9_]*)$/.exec(segment);
        if (!match) {
          throw new TypeError(`invalid parameter segment: ${segment}`);
        }
        const name = match[1];
        if (names.has(name)) {
          throw new TypeError(`duplicate parameter name: ${name}`);
        }
        names.add(name);
        keys.push(name);
        source += '([^/]+)';
        continue;
      }

      source += escapeRegularExpression(segment);
    }
  }

  const expression = new RegExp(`^${source}$`);

  function matchPath(pathname) {
    const match = expression.exec(pathname);
    if (!match) {
      return null;
    }

    const params = createDictionary();
    for (let index = 0; index < keys.length; index += 1) {
      defineOwn(params, keys[index], decodeURIComponent(match[index + 1]));
    }
    return params;
  }

  return matchPath;
}

function compileMiddlewarePath(pattern) {
  if (typeof pattern !== 'string' || pattern.length === 0) {
    throw new TypeError('path must be a non-empty string');
  }
  if (!pattern.startsWith('/')) {
    throw new TypeError('middleware path must start with "/"');
  }

  const prefix = pattern.length > 1 && pattern.endsWith('/')
    ? pattern.slice(0, -1)
    : pattern;

  return function matchMiddlewarePath(pathname) {
    const matches =
      prefix === '/' ||
      pathname === prefix ||
      (prefix.endsWith('/')
        ? pathname.startsWith(prefix)
        : pathname.startsWith(`${prefix}/`));
    return matches ? createDictionary() : null;
  };
}

function flattenHandlers(values) {
  const handlers = [];
  const activeArrays = new Set();

  function visit(value) {
    if (Array.isArray(value)) {
      if (activeArrays.has(value)) {
        throw new TypeError('handler arrays must not be cyclic');
      }
      activeArrays.add(value);
      for (const nested of value) {
        visit(nested);
      }
      activeArrays.delete(value);
      return;
    }

    if (typeof value !== 'function') {
      throw new TypeError('every handler must be a function');
    }
    handlers.push(value);
  }

  for (const value of values) {
    visit(value);
  }

  if (handlers.length === 0) {
    throw new TypeError('at least one handler is required');
  }
  return handlers;
}

function parseQuery(queryString) {
  const query = createDictionary();
  const searchParams = new URLSearchParams(queryString);

  for (const [key, value] of searchParams) {
    if (!own(query, key)) {
      defineOwn(query, key, value);
    } else if (Array.isArray(query[key])) {
      query[key].push(value);
    } else {
      query[key] = [query[key], value];
    }
  }
  return query;
}

function prepareRequest(request) {
  request.originalUrl = typeof request.url === 'string' ? request.url : '';
  request.path = '/';
  request.query = createDictionary();
  request.params = createDictionary();

  const target = request.originalUrl;
  if (!target.startsWith('/')) {
    throw new URIError('Malformed request target');
  }
  if (/[\u0000-\u001f\u007f]/.test(target)) {
    throw new URIError('Malformed request target');
  }

  const questionMark = target.indexOf('?');
  const pathname = questionMark === -1 ? target : target.slice(0, questionMark);
  const queryString = questionMark === -1 ? '' : target.slice(questionMark + 1);

  request.path = pathname;
  request.query = parseQuery(queryString);
}

function responseHasNoBody(statusCode) {
  return (statusCode >= 100 && statusCode < 200) || statusCode === 204 || statusCode === 304;
}

function decorateResponse(request, response) {
  response.status = function status(code) {
    if (!Number.isInteger(code) || code < 100 || code > 999) {
      throw new RangeError('status code must be an integer from 100 through 999');
    }
    response.statusCode = code;
    return response;
  };

  response.set = function set(field, value) {
    if (typeof field === 'object' && field !== null && !Array.isArray(field)) {
      for (const [name, entry] of Object.entries(field)) {
        response.setHeader(name, entry);
      }
      return response;
    }
    if (typeof field !== 'string' || field.length === 0) {
      throw new TypeError('header name must be a non-empty string');
    }
    response.setHeader(field, value);
    return response;
  };

  response.type = function type(value) {
    if (typeof value !== 'string' || value.trim().length === 0) {
      throw new TypeError('content type must be a non-empty string');
    }
    const requested = value.trim();
    const extension = requested.replace(/^\./, '').toLowerCase();
    const contentType = requested.includes('/')
      ? requested
      : MIME_TYPES[extension] || 'application/octet-stream';
    response.setHeader('Content-Type', contentType);
    return response;
  };

  response.json = function json(value) {
    const serialized = JSON.stringify(value);
    if (!response.hasHeader('Content-Type')) {
      response.setHeader('Content-Type', 'application/json; charset=utf-8');
    }
    return response.send(serialized);
  };

  response.send = function send(value) {
    if (response.writableEnded || response.destroyed) {
      return response;
    }

    let payload;
    if (value === undefined || value === null) {
      payload = Buffer.alloc(0);
    } else if (Buffer.isBuffer(value)) {
      payload = value;
      if (!response.hasHeader('Content-Type')) {
        response.setHeader('Content-Type', 'application/octet-stream');
      }
    } else if (value instanceof ArrayBuffer) {
      payload = Buffer.from(value);
      if (!response.hasHeader('Content-Type')) {
        response.setHeader('Content-Type', 'application/octet-stream');
      }
    } else if (ArrayBuffer.isView(value)) {
      payload = Buffer.from(value.buffer, value.byteOffset, value.byteLength);
      if (!response.hasHeader('Content-Type')) {
        response.setHeader('Content-Type', 'application/octet-stream');
      }
    } else if (typeof value === 'object') {
      return response.json(value);
    } else {
      payload = Buffer.from(String(value));
      if (!response.hasHeader('Content-Type')) {
        response.setHeader('Content-Type', 'text/plain; charset=utf-8');
      }
    }

    if (responseHasNoBody(response.statusCode)) {
      response.removeHeader('Content-Length');
      response.removeHeader('Transfer-Encoding');
      response.end();
      return response;
    }

    response.setHeader('Content-Length', String(payload.length));
    if (String(request.method || '').toUpperCase() === 'HEAD') {
      response.end();
    } else {
      response.end(payload);
    }
    return response;
  };
}

function simpleResponse(request, response, statusCode, body) {
  if (response.writableEnded || response.destroyed) {
    return;
  }
  if (response.headersSent) {
    response.end();
    return;
  }

  const payload = Buffer.from(body);
  response.statusCode = statusCode;
  response.setHeader('Content-Type', 'text/plain; charset=utf-8');
  response.setHeader('Content-Length', String(payload.length));
  if (String(request.method || '').toUpperCase() === 'HEAD') {
    response.end();
  } else {
    response.end(payload);
  }
}

function createApplication() {
  const stack = [];

  function application(request, response) {
    return application.handle(request, response);
  }

  function register(kind, method, path, handlerValues) {
    const matcher =
      kind === 'route' ? compileRoutePath(path) : compileMiddlewarePath(path);
    const handlers = flattenHandlers(handlerValues);
    const registration = {};
    for (const handler of handlers) {
      stack.push({ kind, method, matcher, handler, registration });
    }
    return application;
  }

  application.use = function use(...args) {
    let path = '/';
    let handlerValues = args;
    if (typeof args[0] === 'string') {
      path = args[0];
      handlerValues = args.slice(1);
    }
    return register('middleware', null, path, handlerValues);
  };

  for (const method of ['get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'all']) {
    application[method] = function route(path, ...handlerValues) {
      return register('route', method.toUpperCase(), path, handlerValues);
    };
  }

  application.handle = function handle(request, response, done) {
    let initialError = NO_ERROR;
    try {
      prepareRequest(request);
    } catch (error) {
      initialError = error;
    }
    decorateResponse(request, response);

    const requestMethod = String(request.method || 'GET').toUpperCase();
    const paramsByRegistration = new Map();
    let finalized = false;

    function finish(errorState) {
      if (finalized) {
        return;
      }
      finalized = true;

      if (typeof done === 'function') {
        done(errorState === NO_ERROR ? undefined : errorState);
        return;
      }
      if (errorState !== NO_ERROR) {
        simpleResponse(request, response, 500, 'Internal Server Error');
      } else {
        simpleResponse(request, response, 404, 'Not Found');
      }
    }

    function methodMatches(layer) {
      if (layer.kind === 'middleware' || layer.method === 'ALL') {
        return true;
      }
      if (layer.method === requestMethod) {
        return true;
      }
      return false;
    }

    function dispatch(startIndex, errorState) {
      if (finalized || response.writableEnded || response.destroyed) {
        finalized = true;
        return;
      }

      let index = startIndex;
      while (index < stack.length) {
        const layer = stack[index];
        const layerIndex = index;
        index += 1;

        const isErrorHandler = layer.handler.length === 4;
        if ((errorState === NO_ERROR && isErrorHandler) || (errorState !== NO_ERROR && !isErrorHandler)) {
          continue;
        }
        if (!methodMatches(layer)) {
          continue;
        }

        let params;
        if (paramsByRegistration.has(layer.registration)) {
          params = paramsByRegistration.get(layer.registration);
        } else {
          try {
            params = layer.matcher(request.path);
          } catch (error) {
            // The route expression matched, but materializing a capture failed.
            // Cache a fresh params object so an error handler declared later in
            // this registration does not repeat the failing decode.
            params = createDictionary();
            paramsByRegistration.set(layer.registration, params);
            errorState = error;
            continue;
          }
          if (params !== null) {
            paramsByRegistration.set(layer.registration, params);
          }
        }
        if (params === null) {
          continue;
        }
        request.params = params;

        let called = false;
        function next(nextError) {
          if (called || finalized) {
            return;
          }
          called = true;
          const hasError =
            arguments.length > 0 &&
            nextError !== undefined &&
            nextError !== null;
          dispatch(layerIndex + 1, hasError ? nextError : NO_ERROR);
        }

        let result;
        try {
          result = isErrorHandler
            ? layer.handler(errorState, request, response, next)
            : layer.handler(request, response, next);
        } catch (error) {
          if (!called) {
            called = true;
            dispatch(layerIndex + 1, error);
          }
          return;
        }

        if (result && (typeof result === 'object' || typeof result === 'function')) {
          Promise.resolve(result).catch((error) => {
            if (!called && !finalized) {
              called = true;
              dispatch(layerIndex + 1, error);
            }
          });
        }
        return;
      }

      finish(errorState);
    }

    dispatch(0, initialError);
    return response;
  };

  application.listen = function listen(...args) {
    const server = http.createServer(application);
    return server.listen(...args);
  };

  return application;
}

module.exports = createApplication;
