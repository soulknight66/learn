'use strict';

const http = require('node:http');

function sendText(res, text) {
  res.statusCode = 200;
  res.setHeader('content-type', 'text/plain; charset=utf-8');
  res.setHeader('content-length', String(text.length));
  res.end(text);
}

function createServer() {
  return http.createServer((_req, res) => sendText(res, 'café'));
}

module.exports = { createServer, sendText };
