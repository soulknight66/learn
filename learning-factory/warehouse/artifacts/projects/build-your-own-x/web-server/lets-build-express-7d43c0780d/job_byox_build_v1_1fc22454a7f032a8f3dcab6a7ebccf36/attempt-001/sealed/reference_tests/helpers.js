'use strict';

const http = require('node:http');

const OPERATION_TIMEOUT_MS = 3000;
const MAX_RESPONSE_BYTES = 1024 * 1024;

async function startServer(listener) {
  const server =
    listener && typeof listener.listen === 'function'
      ? listener.listen(0, '127.0.0.1')
      : http.createServer(listener).listen(0, '127.0.0.1');
  try {
    if (!server.listening) {
      await new Promise((resolve, reject) => {
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
        const onListening = () => finish();
        const onError = (error) => finish(error);
        const timer = setTimeout(
          () => finish(new Error('server did not start within 3000ms')),
          OPERATION_TIMEOUT_MS,
        );
        server.once('listening', onListening);
        server.once('error', onError);
      });
    }
    return server;
  } catch (error) {
    try {
      await stopServer(server);
    } catch {
      // Preserve the startup error; cleanup already had its own absolute deadline.
    }
    throw error;
  }
}

async function stopServer(server) {
  await new Promise((resolve, reject) => {
    let settled = false;
    const finish = (error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (error && error.code !== 'ERR_SERVER_NOT_RUNNING') reject(error);
      else resolve();
    };
    const timer = setTimeout(
      () => finish(new Error('server did not stop within 3000ms')),
      OPERATION_TIMEOUT_MS,
    );
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

async function withServer(listener, callback) {
  const server = await startServer(listener);
  try {
    return await callback(server);
  } finally {
    await stopServer(server);
  }
}

function request(server, options = {}) {
  const address = server.address();
  const method = options.method || 'GET';
  const path = options.path || '/';

  return new Promise((resolve, reject) => {
    let outgoing;
    let settled = false;
    const timer = setTimeout(() => {
      finish(new Error(`${method} ${path} exceeded ${OPERATION_TIMEOUT_MS}ms`));
    }, OPERATION_TIMEOUT_MS);

    function finish(error, value) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (error) {
        if (outgoing && !outgoing.destroyed) outgoing.destroy();
        reject(error);
      } else {
        resolve(value);
      }
    }

    try {
      outgoing = http.request(
        {
          host: '127.0.0.1',
          port: address.port,
          method,
          path,
          headers: options.headers,
          agent: false,
        },
        (incoming) => {
          const chunks = [];
          let receivedBytes = 0;
          incoming.on('data', (chunk) => {
            receivedBytes += chunk.length;
            if (receivedBytes > MAX_RESPONSE_BYTES) {
              finish(
                new Error(`${method} ${path} exceeded ${MAX_RESPONSE_BYTES} response bytes`),
              );
              return;
            }
            chunks.push(chunk);
          });
          incoming.on('aborted', () => finish(new Error(`${method} ${path} response aborted`)));
          incoming.on('error', finish);
          incoming.on('end', () => {
            const buffer = Buffer.concat(chunks);
            finish(null, {
              statusCode: incoming.statusCode,
              headers: incoming.headers,
              body: buffer.toString('utf8'),
              buffer,
            });
          });
        },
      );

      outgoing.on('error', finish);
      if (options.body !== undefined) {
        outgoing.write(options.body);
      }
      outgoing.end();
    } catch (error) {
      finish(error);
    }
  });
}

module.exports = { request, startServer, stopServer, withServer };
