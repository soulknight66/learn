'use strict';

const DECORATED = Symbol('responseDecorated');
const BODYLESS_ENTITY_HEADERS = Object.freeze([
  'content-encoding',
  'content-language',
  'content-length',
  'content-location',
  'content-md5',
  'content-range',
  'content-type',
  'digest',
  'trailer',
  'transfer-encoding'
]);

function bodyIsForbidden(statusCode) {
  return (statusCode >= 100 && statusCode < 200) || statusCode === 204 || statusCode === 304;
}

function assertWritable(res) {
  if (res.writableEnded || res.destroyed) {
    throw new Error('response has already ended');
  }
}

function removeEntityHeaders(res) {
  for (const name of BODYLESS_ENTITY_HEADERS) {
    res.removeHeader(name);
  }
}

function finish(res, requestMethod, buffer, defaultType) {
  assertWritable(res);

  if (bodyIsForbidden(res.statusCode)) {
    removeEntityHeaders(res);
    res.end();
    return res;
  }

  if (defaultType && !res.hasHeader('content-type')) {
    res.setHeader('content-type', defaultType);
  }
  res.setHeader('content-length', String(buffer.length));

  if (requestMethod === 'HEAD') {
    res.end();
  } else {
    res.end(buffer);
  }
  return res;
}

function decorateResponse(res, requestMethod) {
  if (res[DECORATED]) {
    return res;
  }
  Object.defineProperty(res, DECORATED, { value: true });

  res.status = function status(code) {
    assertWritable(res);
    if (!Number.isInteger(code) || code < 100 || code > 999) {
      throw new RangeError('status code must be an integer from 100 through 999');
    }
    res.statusCode = code;
    return res;
  };

  res.set = function set(name, value) {
    assertWritable(res);
    res.setHeader(name, value);
    return res;
  };

  res.json = function json(value) {
    assertWritable(res);
    const serialized = JSON.stringify(value);
    const buffer = serialized === undefined
      ? Buffer.alloc(0)
      : Buffer.from(serialized, 'utf8');
    return finish(res, requestMethod, buffer, 'application/json; charset=utf-8');
  };

  res.send = function send(value) {
    assertWritable(res);

    if (value !== null && typeof value === 'object' && !Buffer.isBuffer(value)) {
      return res.json(value);
    }
    if (Buffer.isBuffer(value)) {
      return finish(res, requestMethod, value, 'application/octet-stream');
    }
    if (value === null || value === undefined) {
      return finish(res, requestMethod, Buffer.alloc(0), null);
    }

    return finish(
      res,
      requestMethod,
      Buffer.from(String(value), 'utf8'),
      'text/plain; charset=utf-8'
    );
  };

  return res;
}

module.exports = {
  BODYLESS_ENTITY_HEADERS,
  decorateResponse,
  bodyIsForbidden,
  finish
};
