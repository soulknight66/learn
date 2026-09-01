'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadFactory, withServer } = require('./_helpers');

test('middleware runs in registration order and supports nested handler arrays', async () => {
  const app = loadFactory()();

  app.use((req, _res, next) => {
    req.steps = ['first'];
    next();
  });
  app.use([
    (req, _res, next) => {
      req.steps.push('second');
      next();
    },
    [(req, res) => {
      req.steps.push('third');
      res.setHeader('Content-Type', 'application/json');
      res.end(JSON.stringify(req.steps));
    }]
  ]);

  await withServer(app, async (request) => {
    const response = await request({ path: '/' });
    assert.equal(response.status, 200);
    assert.deepEqual(JSON.parse(response.body), ['first', 'second', 'third']);
  });
});

test('middleware prefixes honor path-segment boundaries', async () => {
  const app = loadFactory()();

  app.use('/api', (_req, res, next) => {
    res.setHeader('X-Api-Middleware', 'yes');
    next();
  });
  app.use((_req, res) => res.end('done'));

  await withServer(app, async (request) => {
    const exact = await request({ path: '/api' });
    const child = await request({ path: '/api/users?active=1' });
    const falsePrefix = await request({ path: '/apix' });

    assert.equal(exact.headers['x-api-middleware'], 'yes');
    assert.equal(child.headers['x-api-middleware'], 'yes');
    assert.equal(falsePrefix.headers['x-api-middleware'], undefined);
  });
});

test('next(err), throws, and arity-four middleware use error flow', async () => {
  const app = loadFactory()();

  app.use('/throw', () => {
    throw new Error('boom');
  });
  app.use('/next-error', (_req, _res, next) => next(new Error('passed')));
  app.use((_req, _res, next) => next());
  app.use((err, _req, res, _next) => {
    res.statusCode = 418;
    res.end(`caught:${err.message}`);
  });

  await withServer(app, async (request) => {
    const thrown = await request({ path: '/throw' });
    const passed = await request({ path: '/next-error' });
    assert.equal(thrown.status, 418);
    assert.equal(thrown.body, 'caught:boom');
    assert.equal(passed.status, 418);
    assert.equal(passed.body, 'caught:passed');
  });
});

test('one next callback cannot dispatch downstream handlers twice', async () => {
  const app = loadFactory()();
  let downstreamRuns = 0;

  app.use((_req, _res, next) => {
    next();
    next();
  });
  app.use((_req, res) => {
    downstreamRuns += 1;
    res.end(String(downstreamRuns));
  });

  await withServer(app, async (request) => {
    const response = await request({ path: '/' });
    assert.equal(response.body, '1');
    assert.equal(downstreamRuns, 1);
  });
});

