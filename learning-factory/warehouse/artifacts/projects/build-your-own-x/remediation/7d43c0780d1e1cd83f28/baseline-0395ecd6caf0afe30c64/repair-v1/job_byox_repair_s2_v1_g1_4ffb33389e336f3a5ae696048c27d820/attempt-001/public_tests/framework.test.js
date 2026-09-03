'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const { request, withServer } = require('./helpers');

const submissionRoot = process.env.SUBMISSION_ROOT
  ? path.resolve(process.env.SUBMISSION_ROOT)
  : path.join(__dirname, '..', 'starter');
const tiny = require(submissionRoot);

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

test('exports the documented application API', () => {
  assert.equal(typeof tiny, 'function');
  assert.equal(tiny.createApplication, tiny);
  assert.equal(typeof tiny.json, 'function');
  assert.equal(typeof tiny.HttpError, 'function');

  const app = tiny();
  assert.equal(typeof app, 'function');
  for (const name of ['use', 'get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'listen']) {
    assert.equal(typeof app[name], 'function', `missing app.${name}`);
  }
});

test('runs middleware in order and exposes params plus duplicate query values', async () => {
  const app = tiny();
  const events = [];

  app.use(async (_req, _res, next) => {
    events.push('outer:before');
    await next();
    events.push('outer:after');
  });
  app.use('/items', async (_req, _res, next) => {
    events.push('scoped');
    await next();
  });
  app.get('/items/:id', (req, res) => {
    events.push('route');
    res.json({
      id: req.params.id,
      colors: req.query.getAll('color'),
      path: req.path
    });
  });

  await withServer(app, async (server) => {
    const response = await request(server, {
      path: '/items/a%20b?color=red&color=blue'
    });
    assert.equal(response.status, 200);
    assert.deepEqual(JSON.parse(response.text), {
      id: 'a b',
      colors: ['red', 'blue'],
      path: '/items/a%20b'
    });
  });

  assert.deepEqual(events, ['outer:before', 'scoped', 'route', 'outer:after']);
});

test('parses JSON and maps malformed JSON to a client error', async () => {
  const app = tiny();
  app.use(tiny.json({ limit: 128 }));
  app.post('/echo', (req, res) => res.status(201).json({ received: req.body }));

  await withServer(app, async (server) => {
    const accepted = await request(server, {
      method: 'POST',
      path: '/echo',
      headers: { 'content-type': 'application/json; charset=utf-8' },
      body: '{"ok":true}'
    });
    assert.equal(accepted.status, 201);
    assert.deepEqual(JSON.parse(accepted.text), { received: { ok: true } });

    const rejected = await request(server, {
      method: 'POST',
      path: '/echo',
      headers: { 'content-type': 'application/json' },
      body: '{"broken":'
    });
    assert.equal(rejected.status, 400);
    assert.equal(JSON.parse(rejected.text).error.status, 400);
  });
});

test('distinguishes missing paths, unsupported methods, and automatic OPTIONS', async () => {
  const app = tiny();
  app.get('/known', (_req, res) => res.send('yes'));
  app.post('/known', (_req, res) => res.send('posted'));

  await withServer(app, async (server) => {
    const missing = await request(server, { path: '/missing' });
    assert.equal(missing.status, 404);

    const unsupported = await request(server, { method: 'PUT', path: '/known' });
    assert.equal(unsupported.status, 405);
    assert.equal(unsupported.headers.allow, 'GET, HEAD, POST, OPTIONS');

    const options = await request(server, { method: 'OPTIONS', path: '/known' });
    assert.equal(options.status, 204);
    assert.equal(options.headers.allow, 'GET, HEAD, POST, OPTIONS');
    assert.equal(options.body.length, 0);
  });
});

test('uses 404 when a supported method handler falls through', async () => {
  const app = tiny();
  const explicitHeadCalls = [];

  app.get('/chain', async (_req, _res, next) => next());
  app.get('/chain', async (_req, _res, next) => next());
  app.get('/returned', () => undefined);
  app.get('/fallback-head', async (_req, _res, next) => next());
  app.head('/explicit-head', () => {
    explicitHeadCalls.push('HEAD');
  });
  app.get('/explicit-head', (_req, res) => {
    explicitHeadCalls.push('GET');
    res.send('must not run');
  });

  await withServer(app, async (server) => {
    for (const options of [
      { method: 'GET', path: '/chain' },
      { method: 'GET', path: '/returned' },
      { method: 'HEAD', path: '/fallback-head' },
      { method: 'HEAD', path: '/explicit-head' }
    ]) {
      const response = await request(server, options);
      assert.equal(response.status, 404, `${options.method} ${options.path}`);
      assert.equal(response.headers.allow, undefined);
    }
  });

  assert.deepEqual(explicitHeadCalls, ['HEAD']);
});

test('keeps request state isolated behind a deterministic overlap gate', { timeout: 5000 }, async () => {
  const app = tiny();
  const firstAtGate = deferred();
  const secondAtGate = deferred();
  const releaseFirst = deferred();

  app.use(tiny.json({ limit: 128 }));
  app.post('/jobs/:id', async (req, res) => {
    const before = { id: req.params.id, value: req.body.value };
    if (before.id === 'alpha') {
      firstAtGate.resolve();
      await releaseFirst.promise;
    } else {
      secondAtGate.resolve();
    }

    const status = req.params.id === 'alpha' ? 201 : 202;
    res
      .status(status)
      .set('x-request-id', req.params.id)
      .json({
        before,
        after: { id: req.params.id, value: req.body.value }
      });
  });

  await withServer(app, async (server) => {
    const pending = [];
    try {
      const first = request(server, {
        method: 'POST',
        path: '/jobs/alpha',
        headers: { 'content-type': 'application/json' },
        body: '{"value":"first"}'
      });
      pending.push(first);
      await within(firstAtGate.promise, 'first request gate');

      const second = request(server, {
        method: 'POST',
        path: '/jobs/beta',
        headers: { 'content-type': 'application/json' },
        body: '{"value":"second"}'
      });
      pending.push(second);
      await within(secondAtGate.promise, 'second request gate');
      releaseFirst.resolve();

      const [firstResponse, secondResponse] = await Promise.all(pending);
      assert.equal(firstResponse.status, 201);
      assert.equal(firstResponse.headers['x-request-id'], 'alpha');
      assert.deepEqual(JSON.parse(firstResponse.text), {
        before: { id: 'alpha', value: 'first' },
        after: { id: 'alpha', value: 'first' }
      });
      assert.equal(secondResponse.status, 202);
      assert.equal(secondResponse.headers['x-request-id'], 'beta');
      assert.deepEqual(JSON.parse(secondResponse.text), {
        before: { id: 'beta', value: 'second' },
        after: { id: 'beta', value: 'second' }
      });
    } finally {
      releaseFirst.resolve();
      await Promise.allSettled(pending);
    }
  });
});
