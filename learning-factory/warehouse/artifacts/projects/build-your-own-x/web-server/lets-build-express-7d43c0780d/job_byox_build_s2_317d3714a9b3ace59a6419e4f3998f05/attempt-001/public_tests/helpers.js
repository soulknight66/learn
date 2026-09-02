'use strict';

const http = require('node:http');

async function startServer(app) {
  const server = http.createServer(app);
  await new Promise((resolve, reject) => {
    const onError = (error) => {
      server.off('listening', onListening);
      reject(error);
    };
    const onListening = () => {
      server.off('error', onError);
      resolve();
    };
    server.once('error', onError);
    server.once('listening', onListening);
    server.listen(0, '127.0.0.1');
  });
  return server;
}

async function closeServer(server) {
  if (!server.listening) {
    return;
  }
  await new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()));
  });
}

function request(server, options = {}) {
  const address = server.address();
  const method = options.method || 'GET';
  const path = options.path || '/';
  const headers = { ...(options.headers || {}) };
  const body = options.body;

  if (
    body !== undefined
    && headers['content-length'] === undefined
    && options.omitContentLength !== true
  ) {
    headers['content-length'] = Buffer.byteLength(body);
  }

  return new Promise((resolve, reject) => {
    const outgoing = http.request({
      host: '127.0.0.1',
      port: address.port,
      method,
      path,
      headers
    });
    outgoing.setTimeout(2000, () => outgoing.destroy(new Error('request timed out')));
    outgoing.once('error', reject);
    outgoing.once('response', (response) => {
      const chunks = [];
      response.on('data', (chunk) => chunks.push(chunk));
      response.once('aborted', () => reject(new Error('response aborted')));
      response.once('error', reject);
      response.once('end', () => {
        const buffer = Buffer.concat(chunks);
        resolve({
          status: response.statusCode,
          headers: response.headers,
          body: buffer,
          text: buffer.toString('utf8')
        });
      });
    });
    if (body !== undefined) {
      outgoing.write(body);
    }
    outgoing.end();
  });
}

async function withServer(app, callback) {
  const server = await startServer(app);
  try {
    return await callback(server);
  } finally {
    await closeServer(server);
  }
}

module.exports = { startServer, closeServer, request, withServer };
