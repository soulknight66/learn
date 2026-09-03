'use strict';

class HttpError extends Error {
  constructor(status, message, options = {}) {
    super(message, options.cause === undefined ? undefined : { cause: options.cause });
    this.name = 'HttpError';
    this.status = status;
    this.expose = options.expose === undefined ? status < 500 : Boolean(options.expose);
    this.headers = options.headers === undefined ? null : options.headers;
    this.code = options.code;
  }
}

module.exports = { HttpError };
