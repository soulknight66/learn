'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadFactory, withServer } = require('./_helpers');

test('status, set, type, and send are chainable response helpers', async () => {
  const app = loadFactory()();

  app.get('/created', (_req, res) => {
    const returned = res.status(201).set('X-Result', 'created').type('html');
    assert.equal(returned, res);
    assert.equal(res.send('<p>ok</p>'), res);
  });

  await withServer(app, async (request) => {
    const response = await request({ path: '/created' });
    assert.equal(response.status, 201);
    assert.equal(response.headers['x-result'], 'created');
    assert.equal(response.headers['content-type'], 'text/html; charset=utf-8');
    assert.equal(response.body, '<p>ok</p>');
  });
});

test('json serializes data without replacing an explicit content type', async () => {
  const app = loadFactory()();

  app.get('/json', (_req, res) => res.json({ ok: true, count: 2 }));
  app.get('/custom', (_req, res) => {
    res.set('Content-Type', 'application/problem+json');
    res.json({ problem: true });
  });

  await withServer(app, async (request) => {
    const json = await request({ path: '/json' });
    const custom = await request({ path: '/custom' });
    assert.equal(json.headers['content-type'], 'application/json; charset=utf-8');
    assert.deepEqual(JSON.parse(json.body), { ok: true, count: 2 });
    assert.equal(custom.headers['content-type'], 'application/problem+json');
    assert.deepEqual(JSON.parse(custom.body), { problem: true });
  });
});

test('HEAD routes select status and headers but send no body bytes', async () => {
  const app = loadFactory()();

  app.head('/metadata', (_req, res) => {
    res.status(202).set('X-Head-Handler', 'yes').send('must-not-arrive');
  });

  await withServer(app, async (request) => {
    const response = await request({ method: 'HEAD', path: '/metadata' });
    assert.equal(response.status, 202);
    assert.equal(response.headers['x-head-handler'], 'yes');
    assert.equal(response.body, '');
  });
});

test('fulfilled async handlers may respond after awaiting', async () => {
  const app = loadFactory()();

  app.get('/later', async (_req, res) => {
    await Promise.resolve();
    res.send('later');
  });

  await withServer(app, async (request) => {
    const response = await request({ path: '/later' });
    assert.equal(response.status, 200);
    assert.equal(response.body, 'later');
  });
});

test('a rejected async handler reaches error middleware', async () => {
  const app = loadFactory()();

  app.get('/reject', async () => {
    await Promise.resolve();
    throw new Error('async boom');
  });
  app.use((err, _req, res, _next) => {
    res.status(422).json({ caught: err.message });
  });

  await withServer(app, async (request) => {
    const response = await request({ path: '/reject' });
    assert.equal(response.status, 422);
    assert.deepEqual(JSON.parse(response.body), { caught: 'async boom' });
  });
});

test('an unhandled rejection uses the deterministic, non-leaking 500', async () => {
  const app = loadFactory()();

  app.get('/unhandled', async () => {
    throw new Error('private detail');
  });

  await withServer(app, async (request) => {
    const response = await request({ path: '/unhandled' });
    assert.equal(response.status, 500);
    assert.equal(response.headers['content-type'], 'text/plain; charset=utf-8');
    assert.equal(response.body, 'Internal Server Error');
    assert.equal(response.body.includes('private detail'), false);
  });
});

