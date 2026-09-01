'use strict';

const http = require('node:http');
const path = require('node:path');

const OPERATION_TIMEOUT_MS = 3000;
const MAX_RESPONSE_BYTES = 1024 * 1024;

const defaultEntry = path.resolve(__dirname, '..', 'starter', 'src', 'index.js');
const candidateEntry = process.env.MINI_EXPRESS_ENTRY
  ? path.resolve(process.cwd(), process.env.MINI_EXPRESS_ENTRY)
  : defaultEntry;

function loadFactory() {
  return require(candidateEntry);
}

function waitForListening(server) {
  if (server.listening) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    let settled = false;

    const finish = (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      server.off('listening', onListening);
      server.off('error', onError);
      if (error) reject(error);
      else resolve();
    };
    const onListening = () => {
      finish();
    };
    const onError = (error) => {
      finish(error);
    };
    const timer = setTimeout(() => {
      finish(new Error(`server did not start within ${OPERATION_TIMEOUT_MS}ms`));
    }, OPERATION_TIMEOUT_MS);

    server.once('listening', onListening);
    server.once('error', onError);
  });
}

function request(server, options = {}) {
  const address = server.address();
  const method = options.method || 'GET';
  const requestPath = options.path || '/';

  return new Promise((resolve, reject) => {
    let req;
    let settled = false;

    const timer = setTimeout(() => {
      finish(new Error(
        `${method} ${requestPath} exceeded ${OPERATION_TIMEOUT_MS}ms`
      ));
    }, OPERATION_TIMEOUT_MS);

    function finish(error, value) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (error) {
        if (req && !req.destroyed) req.destroy();
        reject(error);
      } else {
        resolve(value);
      }
    }

    try {
      req = http.request({
        host: '127.0.0.1',
        port: address.port,
        method,
        path: requestPath,
        headers: options.headers || {}
      }, (res) => {
        const chunks = [];
        let receivedBytes = 0;

        res.on('data', (chunk) => {
          receivedBytes += chunk.length;
          if (receivedBytes > MAX_RESPONSE_BYTES) {
            finish(new Error(
              `${method} ${requestPath} exceeded ${MAX_RESPONSE_BYTES} response bytes`
            ));
            return;
          }
          chunks.push(chunk);
        });
        res.on('aborted', () => {
          finish(new Error(`${method} ${requestPath} response was aborted`));
        });
        res.on('error', finish);
        res.on('end', () => {
          finish(null, {
            status: res.statusCode,
            headers: res.headers,
            body: Buffer.concat(chunks).toString('utf8')
          });
        });
      });

      req.on('error', finish);
      if (options.body !== undefined) {
        req.write(options.body);
      }
      req.end();
    } catch (error) {
      finish(error);
    }
  });
}

function closeServer(server) {
  return new Promise((resolve, reject) => {
    let settled = false;

    const timer = setTimeout(() => {
      finish(new Error(`server did not close within ${OPERATION_TIMEOUT_MS}ms`));
    }, OPERATION_TIMEOUT_MS);

    function finish(error) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (error && error.code !== 'ERR_SERVER_NOT_RUNNING') reject(error);
      else resolve();
    }

    try {
      server.close(finish);
      if (typeof server.closeAllConnections === 'function') {
        server.closeAllConnections();
      }
    } catch (error) {
      finish(error);
    }
  });
}

async function withServer(app, callback) {
  const server = app.listen(0, '127.0.0.1');
  try {
    await waitForListening(server);
    return await callback((options) => request(server, options), server);
  } finally {
    await closeServer(server);
  }
}

module.exports = {
  loadFactory,
  request,
  withServer
};
