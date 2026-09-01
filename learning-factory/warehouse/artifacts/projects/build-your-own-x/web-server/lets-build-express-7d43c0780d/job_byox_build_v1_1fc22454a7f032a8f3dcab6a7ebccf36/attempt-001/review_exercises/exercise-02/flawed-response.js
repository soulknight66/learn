"use strict";

function install(req, res) {
  res.status = function status(code) {
    this.statusCode = code || 200;
    return this;
  };

  res.json = function json(value) {
    this.setHeader("content-type", "application/json; charset=utf-8");
    const body = JSON.stringify(value);
    this.setHeader("content-length", String(body.length));
    this.end(body);
    return this;
  };

  res.send = function send(value) {
    let selected = value;
    if (!selected) selected = "";
    if (typeof selected === "object") return this.json(selected);

    const body = String(selected);
    this.setHeader("content-type", "text/plain; charset=utf-8");
    this.setHeader("content-length", String(body.length));
    this.end(body);
    return this;
  };

  void req;
  return res;
}

module.exports = { install };
