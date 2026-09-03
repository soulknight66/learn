'use strict';

function compose(middleware, terminal) {
  if (!Array.isArray(middleware) || middleware.some((entry) => typeof entry !== 'function')) {
    throw new TypeError('middleware must be an array of functions');
  }
  if (terminal !== undefined && typeof terminal !== 'function') {
    throw new TypeError('terminal must be a function');
  }

  const stack = middleware.slice();

  return function composed(req, res) {
    let furthestIndex = -1;

    function dispatch(index) {
      if (index <= furthestIndex) {
        return Promise.reject(new Error('next() called more than once'));
      }
      furthestIndex = index;

      const handler = index === stack.length ? terminal : stack[index];
      if (handler === undefined) {
        return Promise.resolve();
      }

      try {
        return Promise.resolve(handler(req, res, () => dispatch(index + 1)));
      } catch (error) {
        return Promise.reject(error);
      }
    }

    return dispatch(0);
  };
}

module.exports = { compose };
