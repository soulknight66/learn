'use strict';

const { HttpError } = require('./http-error');

const PARAMETER_NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
const METHOD_TOKEN = /^[A-Z]+$/;
const METHOD_ORDER = ['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'];

function escapeRegularExpression(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
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

function compilePattern(pattern) {
  if (typeof pattern !== 'string' || !pattern.startsWith('/')) {
    throw new TypeError('route pattern must be a string beginning with /');
  }
  if (pattern.includes('?') || pattern.includes('#')) {
    throw new TypeError('route pattern must not include a query or fragment');
  }

  let normalized = pattern;
  if (normalized.length > 1 && normalized.endsWith('/')) {
    normalized = normalized.slice(0, -1);
  }

  const segments = normalized === '/' ? [] : normalized.slice(1).split('/');
  if (segments.some((segment) => segment.length === 0)) {
    throw new TypeError('route pattern must not contain empty segments');
  }

  const parameterNames = [];
  const seenNames = new Set();
  let expression = '^';

  segments.forEach((segment, index) => {
    const marker = segment[0];
    if (marker === ':' || marker === '*') {
      const name = segment.slice(1);
      if (!PARAMETER_NAME.test(name)) {
        throw new TypeError(`invalid route parameter name: ${name || '<empty>'}`);
      }
      if (seenNames.has(name)) {
        throw new TypeError(`duplicate route parameter name: ${name}`);
      }
      if (marker === '*' && index !== segments.length - 1) {
        throw new TypeError('a wildcard parameter must be the final segment');
      }

      seenNames.add(name);
      parameterNames.push(name);
      expression += marker === '*' ? '(?:/(.*))?' : '/([^/]+)';
      return;
    }

    expression += `/${escapeRegularExpression(segment)}`;
  });

  expression += '/?$';
  const regularExpression = new RegExp(expression);

  return Object.freeze({
    pattern,
    parameterNames: Object.freeze(parameterNames.slice()),
    test(pathname) {
      return regularExpression.test(pathname);
    },
    match(pathname) {
      const result = regularExpression.exec(pathname);
      if (result === null) {
        return null;
      }

      const parameters = Object.create(null);
      parameterNames.forEach((name, index) => {
        const captured = result[index + 1];
        parameters[name] = decodeCapture(captured === undefined ? '' : captured);
      });
      return parameters;
    }
  });
}

function methodMatches(routeMethod, requestMethod) {
  return routeMethod === requestMethod || (requestMethod === 'HEAD' && routeMethod === 'GET');
}

function sortMethods(methods) {
  const order = new Map(METHOD_ORDER.map((method, index) => [method, index]));
  return Array.from(methods).sort((left, right) => {
    const leftRank = order.has(left) ? order.get(left) : METHOD_ORDER.length;
    const rightRank = order.has(right) ? order.get(right) : METHOD_ORDER.length;
    return leftRank - rightRank || left.localeCompare(right);
  });
}

class Router {
  createRoute(method, pattern, handlers) {
    if (typeof method !== 'string' || !METHOD_TOKEN.test(method)) {
      throw new TypeError('route method must be an uppercase HTTP token');
    }
    if (!Array.isArray(handlers) || handlers.length === 0) {
      throw new TypeError('a route requires one or more handlers');
    }
    if (handlers.some((handler) => typeof handler !== 'function')) {
      throw new TypeError('route handlers must be functions');
    }

    return Object.freeze({
      type: 'route',
      method,
      compiled: compilePattern(pattern),
      handlers: Object.freeze(handlers.slice())
    });
  }

  match(layer, pathname) {
    return layer.compiled.match(pathname);
  }

  pathMatches(layer, pathname) {
    return layer.compiled.test(pathname);
  }

  allowedMethods(layers, pathname) {
    const methods = new Set();
    for (const layer of layers) {
      if (layer.type === 'route' && this.pathMatches(layer, pathname)) {
        methods.add(layer.method);
      }
    }
    if (methods.has('GET')) {
      methods.add('HEAD');
    }
    if (methods.size > 0) {
      methods.add('OPTIONS');
    }
    return sortMethods(methods);
  }
}

module.exports = {
  Router,
  compilePattern,
  decodeCapture,
  methodMatches,
  sortMethods,
  METHOD_ORDER
};
