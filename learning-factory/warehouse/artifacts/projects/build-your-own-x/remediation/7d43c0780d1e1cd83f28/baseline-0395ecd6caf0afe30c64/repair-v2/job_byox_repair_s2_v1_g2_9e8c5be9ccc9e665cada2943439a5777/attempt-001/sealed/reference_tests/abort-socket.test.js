'use strict';

const assert = require('node:assert/strict');
const { once } = require('node:events');
const net = require('node:net');
const test = require('node:test');
const tiny = require('../reference');
const { closeServer, startServer } = require('../../public_tests/helpers');

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

async function within(promise, label, milliseconds = 1000) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(`${label} timed out`)), milliseconds);
      })
    ]);
  } finally {
    clearTimeout(timer);
  }
}

test('an abort before JSON parser entry settles request work', { timeout: 5000 }, async () => {
  const enteredGate = deferred();
  const abortObserved = deferred();
  const releaseGate = deferred();
  const requestCompleted = deferred();
  const app = tiny();
  let routeCalls = 0;

  app.use(async (req, _res, next) => {
    req.once('aborted', abortObserved.resolve);
    enteredGate.resolve();
    await releaseGate.promise;
    return next();
  });
  app.use(tiny.json({ limit: 32 }));
  app.post('/body', (_req, res) => {
    routeCalls += 1;
    res.send('must not run');
  });

  const server = await startServer((req, res) => {
    Promise.resolve(app(req, res)).then(requestCompleted.resolve, requestCompleted.reject);
  });
  let socket;
  try {
    const address = server.address();
    socket = net.createConnection({ host: '127.0.0.1', port: address.port });
    await within(once(socket, 'connect'), 'socket connection');
    socket.write([
      'POST /body HTTP/1.1',
      'Host: 127.0.0.1',
      'Content-Type: application/json',
      'Content-Length: 2',
      'Connection: close',
      '',
      '{'
    ].join('\r\n'));

    await within(enteredGate.promise, 'gated middleware entry');
    socket.destroy();
    await within(abortObserved.promise, 'request abort');
    releaseGate.resolve();
    await within(requestCompleted.promise, 'request completion');
    assert.equal(routeCalls, 0);
  } finally {
    releaseGate.resolve();
    if (socket !== undefined) {
      socket.destroy();
    }
    await closeServer(server);
  }
});
