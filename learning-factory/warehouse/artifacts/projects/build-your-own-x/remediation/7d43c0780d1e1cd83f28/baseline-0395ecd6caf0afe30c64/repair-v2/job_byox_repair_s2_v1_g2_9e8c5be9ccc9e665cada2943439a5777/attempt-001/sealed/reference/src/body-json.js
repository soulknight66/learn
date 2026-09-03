'use strict';

const { TextDecoder } = require('node:util');
const { HttpError } = require('./http-error');

const DEFAULT_LIMIT = 1024 * 1024;
const BODY_PARSED = Symbol('jsonBodyParsed');
const CONTENT_CODING = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/;

function headerValue(req, name) {
  const value = req.headers && req.headers[name];
  return Array.isArray(value) ? value.join(',') : value;
}

function isJsonMediaType(contentType) {
  if (typeof contentType !== 'string') {
    return false;
  }
  const mediaType = contentType.split(';', 1)[0].trim().toLowerCase();
  return mediaType === 'application/json' || /^[^/\s]+\/[^;\s]+\+json$/.test(mediaType);
}

function contentEncodings(value) {
  if (value === undefined) {
    return [];
  }
  if (typeof value !== 'string') {
    throw new HttpError(400, 'Malformed Content-Encoding', {
      code: 'BAD_CONTENT_ENCODING'
    });
  }

  const encodings = value.split(',').map((member) => member.trim().toLowerCase());
  if (encodings.some((member) => !CONTENT_CODING.test(member))) {
    throw new HttpError(400, 'Malformed Content-Encoding', {
      code: 'BAD_CONTENT_ENCODING'
    });
  }
  return encodings;
}

function declaredLength(req, limit) {
  const value = headerValue(req, 'content-length');
  if (value === undefined) {
    return null;
  }
  if (typeof value !== 'string' || !/^\d+$/.test(value.trim())) {
    throw new HttpError(400, 'Malformed Content-Length', { code: 'BAD_CONTENT_LENGTH' });
  }

  const length = Number(value);
  if (!Number.isSafeInteger(length) || length > limit) {
    throw new HttpError(413, 'Request body too large', { code: 'BODY_TOO_LARGE' });
  }
  return length;
}

function terminalBodyError(req) {
  if (req.errored) {
    return new HttpError(400, 'Request body stream failed', {
      cause: req.errored,
      code: 'BODY_STREAM_ERROR'
    });
  }
  if (
    req.aborted === true
    || req.readableAborted === true
    || (req.destroyed === true && req.readableEnded !== true)
    || (req.closed === true && req.readableEnded !== true)
  ) {
    return new HttpError(400, 'Request body aborted', { code: 'BODY_ABORTED' });
  }
  return null;
}

function readBody(req, limit) {
  const initialError = terminalBodyError(req);
  if (initialError !== null) {
    return Promise.reject(initialError);
  }
  if (req.readableEnded) {
    return Promise.resolve(Buffer.alloc(0));
  }

  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    let settled = false;

    const cleanup = () => {
      req.off('data', onData);
      req.off('end', onEnd);
      req.off('aborted', onAborted);
      req.off('error', onError);
      req.off('close', onClose);
    };

    const fail = (error, drain) => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      if (drain && !req.destroyed) {
        req.resume();
      }
      reject(error);
    };

    const onData = (chunk) => {
      const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      total += bytes.length;
      if (total > limit) {
        fail(
          new HttpError(413, 'Request body too large', { code: 'BODY_TOO_LARGE' }),
          true
        );
        return;
      }
      chunks.push(bytes);
    };

    const onEnd = () => {
      if (settled) {
        return;
      }
      settled = true;
      cleanup();
      resolve(Buffer.concat(chunks, total));
    };

    const onAborted = () => {
      fail(new HttpError(400, 'Request body aborted', { code: 'BODY_ABORTED' }), false);
    };
    const onError = (cause) => {
      fail(new HttpError(400, 'Request body stream failed', {
        cause,
        code: 'BODY_STREAM_ERROR'
      }), false);
    };
    const onClose = () => {
      if (!req.readableEnded) {
        onAborted();
      }
    };

    req.once('aborted', onAborted);
    req.once('error', onError);
    req.once('close', onClose);
    req.once('end', onEnd);
    req.on('data', onData);

    // A terminal event can occur between the preflight check and listener
    // installation. Recheck stream state so that no already-fired event can
    // leave this promise pending.
    const installedError = terminalBodyError(req);
    if (installedError !== null) {
      fail(installedError, false);
    } else if (req.readableEnded) {
      onEnd();
    }
  });
}

function json(options = {}) {
  const limit = options.limit === undefined ? DEFAULT_LIMIT : options.limit;
  if (!Number.isSafeInteger(limit) || limit <= 0) {
    throw new TypeError('json limit must be a positive safe integer');
  }

  return async function parseJson(req, _res, next) {
    if (req[BODY_PARSED] || !isJsonMediaType(headerValue(req, 'content-type'))) {
      return next();
    }

    const encodings = contentEncodings(headerValue(req, 'content-encoding'));
    if (encodings.some((encoding) => encoding !== 'identity')) {
      throw new HttpError(415, 'Unsupported Content-Encoding', {
        code: 'UNSUPPORTED_CONTENT_ENCODING'
      });
    }

    const expectedLength = declaredLength(req, limit);
    const buffer = await readBody(req, limit);
    if (expectedLength !== null && expectedLength !== buffer.length) {
      throw new HttpError(400, 'Content-Length does not match body', {
        code: 'CONTENT_LENGTH_MISMATCH'
      });
    }

    let text;
    try {
      text = new TextDecoder('utf-8', { fatal: true }).decode(buffer);
    } catch (cause) {
      throw new HttpError(400, 'Request body is not valid UTF-8', {
        cause,
        code: 'INVALID_UTF8'
      });
    }

    if (text.length === 0) {
      req.body = null;
    } else {
      try {
        req.body = JSON.parse(text);
      } catch (cause) {
        throw new HttpError(400, 'Malformed JSON body', {
          cause,
          code: 'MALFORMED_JSON'
        });
      }
    }

    Object.defineProperty(req, BODY_PARSED, { value: true });
    return next();
  };
}

module.exports = {
  json,
  isJsonMediaType,
  contentEncodings,
  declaredLength,
  readBody,
  terminalBodyError,
  DEFAULT_LIMIT
};
