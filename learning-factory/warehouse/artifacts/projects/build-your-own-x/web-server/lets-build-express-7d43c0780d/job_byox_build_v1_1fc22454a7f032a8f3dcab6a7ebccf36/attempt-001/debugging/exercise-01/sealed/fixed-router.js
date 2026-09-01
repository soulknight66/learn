"use strict";

const NO_ERROR = Symbol("no error");

function stateFromNext(signals) {
  return signals.length === 0 || signals[0] === undefined || signals[0] === null
    ? NO_ERROR
    : signals[0];
}

function stateFromThrow(value) {
  return value === undefined || value === null
    ? new Error("middleware threw a null or undefined value")
    : value;
}

function run(stack, req, res, done = () => {}) {
  let index = 0;
  let completed = false;

  function finish(error) {
    if (completed) return;
    completed = true;
    done(error === NO_ERROR ? undefined : error);
  }

  function dispatch(error) {
    const handler = stack[index++];
    if (!handler) {
      finish(error);
      return;
    }

    const isErrorHandler = handler.length === 4;
    if (error !== NO_ERROR && !isErrorHandler) {
      dispatch(error);
      return;
    }
    if (error === NO_ERROR && isErrorHandler) {
      dispatch(NO_ERROR);
      return;
    }

    let advanced = false;
    const advanceOnce = (nextError) => {
      if (advanced) return;
      advanced = true;
      dispatch(nextError);
    };
    const nextOnce = (...signals) => advanceOnce(stateFromNext(signals));

    try {
      if (isErrorHandler) {
        handler(error, req, res, nextOnce);
      } else {
        handler(req, res, nextOnce);
      }
    } catch (caught) {
      advanceOnce(stateFromThrow(caught));
    }
  }

  dispatch(NO_ERROR);
}

module.exports = { run };
