'use strict';

const { HttpError } = require('./http-error');

const PARAMETER_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;

function compilePattern(pattern) {
  if (typeof pattern !== 'string' || !pattern.startsWith('/')) {
    throw new TypeError('route pattern must be a string beginning with /');
  }

  // TODO: validate segments and return an object with:
  //   pattern, parameterNames, and match(pathname)
  // `match` should return a null-prototype parameter object or null.
  void PARAMETER_NAME;
  throw new Error('TODO: implement compilePattern');
}

function decodeCapture(value) {
  try {
    return decodeURIComponent(value);
  } catch (cause) {
    throw new HttpError(400, 'Malformed route parameter', {
      cause,
      code: 'MALFORMED_PATH'
    });
  }
}

class Router {
  createRoute(method, pattern, handlers) {
    // TODO: compile once at registration rather than for every request.
    return { type: 'route', method, pattern, handlers };
  }

  match(_layer, _pathname) {
    throw new Error('TODO: implement Router.match');
  }
}

module.exports = { Router, compilePattern, decodeCapture };
