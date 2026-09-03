'use strict';

// Compose middleware into one async request handler. The returned function must preserve onion
// ordering and reject if one middleware invokes its continuation more than once. `terminal` is the
// final `(req, res)` handler.
function compose(middleware, terminal) {
  if (!Array.isArray(middleware) || middleware.some((entry) => typeof entry !== 'function')) {
    throw new TypeError('middleware must be an array of functions');
  }
  if (terminal !== undefined && typeof terminal !== 'function') {
    throw new TypeError('terminal must be a function');
  }

  // TODO: implement a per-request dispatch index. Do not store it at module scope.
  throw new Error('TODO: implement compose');
}

module.exports = { compose };
