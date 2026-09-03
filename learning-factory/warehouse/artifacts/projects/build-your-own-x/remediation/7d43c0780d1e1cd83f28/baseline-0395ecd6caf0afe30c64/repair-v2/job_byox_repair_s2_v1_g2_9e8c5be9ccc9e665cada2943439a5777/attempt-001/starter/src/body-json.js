'use strict';

const DEFAULT_LIMIT = 1024 * 1024;

function json(options = {}) {
  const limit = options.limit === undefined ? DEFAULT_LIMIT : options.limit;
  if (!Number.isSafeInteger(limit) || limit <= 0) {
    throw new TypeError('json limit must be a positive safe integer');
  }

  return async function parseJson(req, _res, next) {
    // TODO: inspect Content-Type and Content-Encoding, enforce both declared and streamed limits,
    // clean up stream listeners, parse UTF-8 JSON, assign req.body, then delegate.
    void req;
    void limit;
    return next();
  };
}

module.exports = { json, DEFAULT_LIMIT };
