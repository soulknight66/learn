'use strict';

class HttpError extends Error {
  constructor(status, message, options = {}) {
    if (!Number.isInteger(status) || status < 400 || status > 599) {
      throw new TypeError('HttpError status must be an integer from 400 through 599');
    }
    if (typeof message !== 'string' || message.length === 0) {
      throw new TypeError('HttpError message must be a non-empty string');
    }

    super(message);
    this.name = 'HttpError';
    this.status = status;
    this.expose = options.expose === undefined ? status < 500 : Boolean(options.expose);
    this.headers = options.headers === undefined ? null : options.headers;
    this.code = options.code;
    if (options.cause !== undefined) {
      this.cause = options.cause;
    }
  }
}

module.exports = { HttpError };
