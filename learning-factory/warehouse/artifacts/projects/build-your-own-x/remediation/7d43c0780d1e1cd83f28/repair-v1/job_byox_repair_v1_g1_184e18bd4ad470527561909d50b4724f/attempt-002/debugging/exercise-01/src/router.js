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

  function dispatch(...signals) {
    const error = signals[0] === NO_ERROR ? NO_ERROR : stateFromNext(signals);
    const handler = stack[index++];
    if (!handler) {
      done(error === NO_ERROR ? undefined : error);
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

    try {
      if (isErrorHandler) {
        handler(error, req, res, dispatch);
      } else {
        handler(req, res, dispatch);
      }
    } catch (caught) {
      dispatch(stateFromThrow(caught));
    }
  }

  dispatch(NO_ERROR);
}

module.exports = { run };
