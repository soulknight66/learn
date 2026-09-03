'use strict';

function decorateResponse(res, requestMethod) {
  if (res.status || res.send || res.json) {
    return res;
  }

  res.status = function status(code) {
    // TODO: validate the complete allowed integer range.
    res.statusCode = code;
    return res;
  };

  res.set = function set(name, value) {
    res.setHeader(name, value);
    return res;
  };

  res.send = function send(_value) {
    // TODO: normalize the body, choose a content type, calculate byte length, and suppress payloads
    // for HEAD and bodyless status codes.
    void requestMethod;
    throw new Error('TODO: implement res.send');
  };

  res.json = function json(_value) {
    // TODO: serialize exactly once and share final body writing with res.send.
    throw new Error('TODO: implement res.json');
  };

  return res;
}

module.exports = { decorateResponse };
