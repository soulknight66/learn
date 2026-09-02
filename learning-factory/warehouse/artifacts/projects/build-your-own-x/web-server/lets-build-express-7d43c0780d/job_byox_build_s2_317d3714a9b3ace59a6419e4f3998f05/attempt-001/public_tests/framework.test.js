'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');
const { request, withServer } = require('./helpers');

const submissionRoot = process.env.SUBMISSION_ROOT
  ? path.resolve(process.env.SUBMISSION_ROOT)
  : path.join(__dirname, '..', 'starter');
const tiny = require(submissionRoot);

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

test('keeps route parameters isolated while requests interleave', async () => {
  const app = tiny();
  app.get('/jobs/:id', async (req, res) => {
    const before = req.params.id;
    await new Promise((resolve) => setTimeout(resolve, Number(before) % 4));
    res.json({ before, after: req.params.id });
  });

  await withServer(app, async (server) => {
    const responses = await Promise.all(
      Array.from({ length: 16 }, (_, id) => request(server, { path: `/jobs/${id}` }))
    );
    responses.forEach((response, id) => {
      assert.equal(response.status, 200);
      assert.deepEqual(JSON.parse(response.text), {
        before: String(id),
        after: String(id)
      });
    });
  });
});
