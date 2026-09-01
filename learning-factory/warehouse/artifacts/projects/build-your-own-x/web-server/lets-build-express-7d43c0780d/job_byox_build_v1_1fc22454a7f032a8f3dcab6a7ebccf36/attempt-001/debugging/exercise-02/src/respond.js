"use strict";

function respond(req, res, value) {
  let body;
  let contentType;

  if (Buffer.isBuffer(value)) {
    body = value;
    contentType = "application/octet-stream";
  } else if (value !== null && typeof value === "object") {
    body = JSON.stringify(value);
    contentType = "application/json; charset=utf-8";
  } else {
    body = String(value);
    contentType = "text/plain; charset=utf-8";
  }

  if (!res.statusCode) res.statusCode = 200;
  res.setHeader("content-type", contentType);
  res.setHeader("content-length", String(body.length));
  res.end(body);
}

module.exports = { respond };
