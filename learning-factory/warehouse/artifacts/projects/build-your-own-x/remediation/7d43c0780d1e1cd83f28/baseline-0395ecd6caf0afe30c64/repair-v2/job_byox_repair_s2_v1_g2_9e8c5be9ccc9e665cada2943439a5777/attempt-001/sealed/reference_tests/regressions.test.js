'use strict';

const assert = require('node:assert/strict');
const { once } = require('node:events');
const http = require('node:http');
const { Duplex, PassThrough } = require('node:stream');
const test = require('node:test');
const tiny = require('../reference');
const { sendError } = require('../reference/src/application');
const {
  BODYLESS_ENTITY_HEADERS,
  decorateResponse
} = require('../reference/src/response');

class MemoryResponse {
  constructor() {
    this.statusCode = 200;
    this.headers = new Map();
    this.headersSent = false;
    this.writableEnded = false;
    this.destroyed = false;
    this.body = Buffer.alloc(0);
  }

  setHeader(name, value) {
    if (this.headersSent) {
      throw new Error('headers already sent');
    }
    this.headers.set(String(name).toLowerCase(), value);
  }

  getHeader(name) {
    return this.headers.get(String(name).toLowerCase());
  }

  hasHeader(name) {
    return this.headers.has(String(name).toLowerCase());
  }

  removeHeader(name) {
    this.headers.delete(String(name).toLowerCase());
  }

  end(value) {
    this.body = value === undefined ? Buffer.alloc(0) : Buffer.from(value);
    this.headersSent = true;
    this.writableEnded = true;
  }

  destroy(error) {
    this.destroyed = true;
    this.destroyError = error;
  }
}

async function dispatch(app, method, url) {
  const req = { method, url, headers: Object.create(null) };
  const res = new MemoryResponse();
  await app(req, res);
  return res;
}

function dispatchJson(app, url, value) {
  const encoded = Buffer.from(JSON.stringify(value), 'utf8');
  const req = new PassThrough();
  req.method = 'POST';
  req.url = url;
  req.headers = {
    'content-type': 'application/json',
    'content-length': String(encoded.length)
  };
  req.complete = true;
  const res = new MemoryResponse();
  const pending = app(req, res);
  req.end(encoded);
  return { pending, res };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

async function within(promise, label) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error(`${label} timed out`)), 250);
      })
    ]);
  } finally {
    clearTimeout(timer);
  }
}

function jsonStream() {
  const req = new PassThrough();
  req.headers = { 'content-type': 'application/json' };
  req.complete = false;
  return req;
}

function assertBodyListenersRemoved(request) {
  for (const event of ['data', 'end', 'aborted', 'error', 'close']) {
    assert.equal(request.listenerCount(event), 0, `${event} listener remains`);
  }
}

async function rejectsWithin(promise, predicate) {
  let timer;
  const bounded = Promise.race([
    promise,
    new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error('body parser did not settle')), 250);
    })
  ]);
  try {
    await assert.rejects(bounded, predicate);
  } finally {
    clearTimeout(timer);
  }
}

test('supported-method fallthrough ends as 404, never 405', async () => {
  const app = tiny();
  const explicitHeadCalls = [];

  app.get('/delegated', async (_req, _res, next) => next());
  app.get('/delegated', async (_req, _res, next) => next());
  app.get('/returned', () => undefined);
  app.get('/fallback-head', async (_req, _res, next) => next());
  app.head('/explicit-head', () => {
    explicitHeadCalls.push('HEAD');
  });
  app.get('/explicit-head', (_req, res) => {
    explicitHeadCalls.push('GET');
    res.send('must not run');
  });

  for (const [method, path] of [
    ['GET', '/delegated'],
    ['GET', '/returned'],
    ['HEAD', '/fallback-head'],
    ['HEAD', '/explicit-head']
  ]) {
    const response = await dispatch(app, method, path);
    assert.equal(response.statusCode, 404, `${method} ${path}`);
    assert.equal(response.getHeader('allow'), undefined);
  }

  assert.deepEqual(explicitHeadCalls, ['HEAD']);

  const unsupported = await dispatch(app, 'POST', '/delegated');
  assert.equal(unsupported.statusCode, 405);
  assert.equal(unsupported.getHeader('allow'), 'GET, HEAD, OPTIONS');
});

test('explicit gates prove request params, bodies, statuses, and headers stay isolated', async () => {
  const firstAtGate = deferred();
  const secondAtGate = deferred();
  const releaseFirst = deferred();
  const app = tiny();
  app.use(tiny.json({ limit: 128 }));
  app.post('/jobs/:id', async (req, res) => {
    const before = { id: req.params.id, value: req.body.value };
    if (before.id === 'alpha') {
      firstAtGate.resolve();
      await releaseFirst.promise;
    } else {
      secondAtGate.resolve();
    }
    res
      .status(req.params.id === 'alpha' ? 201 : 202)
      .set('x-request-id', req.params.id)
      .json({ before, after: { id: req.params.id, value: req.body.value } });
  });

  const first = dispatchJson(app, '/jobs/alpha', { value: 'first' });
  await within(firstAtGate.promise, 'first request gate');
  const second = dispatchJson(app, '/jobs/beta', { value: 'second' });
  await within(secondAtGate.promise, 'second request gate');
  releaseFirst.resolve();
  await within(Promise.all([first.pending, second.pending]), 'request completion');

  assert.equal(first.res.statusCode, 201);
  assert.equal(first.res.getHeader('x-request-id'), 'alpha');
  assert.deepEqual(JSON.parse(first.res.body.toString('utf8')), {
    before: { id: 'alpha', value: 'first' },
    after: { id: 'alpha', value: 'first' }
  });
  assert.equal(second.res.statusCode, 202);
  assert.equal(second.res.getHeader('x-request-id'), 'beta');
  assert.deepEqual(JSON.parse(second.res.body.toString('utf8')), {
    before: { id: 'beta', value: 'second' },
    after: { id: 'beta', value: 'second' }
  });
});

test('JSON parsing rejects abort and destruction that predate listener attachment', async () => {
  const parse = tiny.json({ limit: 32 });

  const aborted = jsonStream();
  aborted.aborted = true;
  aborted.emit('aborted');
  await rejectsWithin(
    parse(aborted, {}, () => undefined),
    (error) => error.code === 'BODY_ABORTED' && error.status === 400
  );
  assertBodyListenersRemoved(aborted);

  const destroyed = jsonStream();
  await new Promise((resolve) => {
    destroyed.once('close', resolve);
    destroyed.destroy();
  });
  await rejectsWithin(
    parse(destroyed, {}, () => undefined),
    (error) => error.code === 'BODY_ABORTED' && error.status === 400
  );
  assertBodyListenersRemoved(destroyed);

  const raced = jsonStream();
  const originalOnce = raced.once;
  raced.once = function once(event, listener) {
    const result = originalOnce.call(this, event, listener);
    if (event === 'end') {
      this.aborted = true;
    }
    return result;
  };
  await rejectsWithin(
    parse(raced, {}, () => undefined),
    (error) => error.code === 'BODY_ABORTED' && error.status === 400
  );
  assertBodyListenersRemoved(raced);
});

test('JSON parsing rejects an error that predates listener attachment', async () => {
  const parse = tiny.json({ limit: 32 });
  const failed = jsonStream();
  const cause = new Error('synthetic stream failure');
  failed.once('error', () => undefined);
  await new Promise((resolve) => {
    failed.once('close', resolve);
    failed.destroy(cause);
  });

  await rejectsWithin(
    parse(failed, {}, () => undefined),
    (error) => error.code === 'BODY_STREAM_ERROR'
      && error.status === 400
      && error.cause === cause
  );
  assertBodyListenersRemoved(failed);
});

test('JSON parsing rejects invalid UTF-8 bytes', async () => {
  const parse = tiny.json({ limit: 32 });
  const request = jsonStream();
  request.complete = true;
  const result = parse(request, {}, () => undefined);
  request.end(Buffer.from([0xc3, 0x28]));
  await assert.rejects(result, (error) => error.code === 'INVALID_UTF8');
});

test('JSON parsing settles and cleans up when a complete stream closes before readable end', async () => {
  const parse = tiny.json({ limit: 32 });
  const request = jsonStream();
  request.complete = true;
  const result = parse(request, {}, () => undefined);

  request.destroy();
  await rejectsWithin(
    result,
    (error) => error.code === 'BODY_ABORTED' && error.status === 400
  );
  assert.equal(request.readableEnded, false);
  assertBodyListenersRemoved(request);
});

test('JSON parsing accepts identity lists and rejects malformed coding members', async () => {
  const parse = tiny.json({ limit: 32 });
  const accepted = jsonStream();
  accepted.complete = true;
  accepted.headers['content-encoding'] = ' identity, IDENTITY ';
  let nextCalls = 0;
  const acceptedResult = parse(accepted, {}, () => {
    nextCalls += 1;
  });
  accepted.end('{"ok":true}');
  await acceptedResult;
  assert.deepEqual(accepted.body, { ok: true });
  assert.equal(nextCalls, 1);
  assertBodyListenersRemoved(accepted);

  for (const value of ['', 'identity,', ', identity', 'identity;level=1', 7]) {
    const malformed = jsonStream();
    malformed.headers['content-encoding'] = value;
    await assert.rejects(
      parse(malformed, {}, () => undefined),
      (error) => error.code === 'BAD_CONTENT_ENCODING' && error.status === 400
    );
    assertBodyListenersRemoved(malformed);
    malformed.destroy();
  }

  const unsupported = jsonStream();
  unsupported.headers['content-encoding'] = 'identity, gzip';
  await assert.rejects(
    parse(unsupported, {}, () => undefined),
    (error) => error.code === 'UNSUPPORTED_CONTENT_ENCODING' && error.status === 415
  );
  assertBodyListenersRemoved(unsupported);
  unsupported.destroy();
});

test('body-forbidden statuses remove the defined entity and framing headers', () => {
  for (const status of [199, 204, 304]) {
    const response = decorateResponse(new MemoryResponse(), 'GET');
    for (const name of BODYLESS_ENTITY_HEADERS) {
      response.set(name, name === 'content-length' ? '12' : 'synthetic');
    }

    response.status(status).send('must disappear');

    assert.equal(response.body.length, 0, `status ${status} wrote a payload`);
    for (const name of BODYLESS_ENTITY_HEADERS) {
      assert.equal(response.hasHeader(name), false, `status ${status} retained ${name}`);
    }
  }
});

test('native error responses replace stale framing and encoded representation headers', async () => {
  const chunks = [];
  const socket = new Duplex({
    read() {},
    write(chunk, _encoding, callback) {
      chunks.push(Buffer.from(chunk));
      callback();
    }
  });
  const response = new http.ServerResponse({
    method: 'GET',
    httpVersionMajor: 1,
    httpVersionMinor: 1,
    shouldKeepAlive: false
  });
  response.assignSocket(socket);
  response.setHeader('transfer-encoding', 'chunked');
  response.setHeader('content-encoding', 'gzip');
  response.setHeader('content-range', 'bytes 0-3/10');
  response.setHeader('trailer', 'x-checksum');

  const error = new tiny.HttpError(429, 'Slow down', {
    headers: {
      'retry-after': '3',
      'content-encoding': 'br',
      'x-untrusted-error-metadata': 'must not be copied'
    }
  });
  const finished = once(response, 'finish');
  sendError(response, error);
  await finished;
  socket.destroy();

  const body = Buffer.from(JSON.stringify({
    error: { status: 429, message: 'Slow down' }
  }), 'utf8');
  const serialized = Buffer.concat(chunks).toString('latin1');
  const headerBlock = serialized.split('\r\n\r\n', 1)[0];
  assert.match(headerBlock, /^HTTP\/1\.1 429 /);
  assert.match(headerBlock, /\r\nContent-Type: application\/json; charset=utf-8\r\n/i);
  assert.match(headerBlock, new RegExp(`\\r\\nContent-Length: ${body.length}\\r\\n`, 'i'));
  assert.match(headerBlock, /\r\nRetry-After: 3\r\n/i);
  assert.doesNotMatch(headerBlock, /\r\nTransfer-Encoding:/i);
  assert.doesNotMatch(headerBlock, /\r\nContent-Encoding:/i);
  assert.doesNotMatch(headerBlock, /\r\nContent-Range:/i);
  assert.doesNotMatch(headerBlock, /\r\nTrailer:/i);
  assert.doesNotMatch(headerBlock, /\r\nX-Untrusted-Error-Metadata:/i);
  assert.equal(serialized.endsWith(body.toString('latin1')), true);
});
