"use strict";

function respond(req, res, value) {
  let body;
  let contentType;

  if (Buffer.isBuffer(value)) {
    body = value;
    contentType = "application/octet-stream";
  } else if (value !== null && typeof value === "object") {
    body = Buffer.from(JSON.stringify(value), "utf8");
    contentType = "application/json; charset=utf-8";
  } else {
    body = Buffer.from(String(value), "utf8");
    contentType = "text/plain; charset=utf-8";
  }

  if (!res.statusCode) res.statusCode = 200;
  res.setHeader("content-type", contentType);
  res.setHeader("content-length", String(body.length));
  if (String(req.method).toUpperCase() === "HEAD") {
    res.end();
  } else {
    res.end(body);
  }
}

module.exports = { respond };
