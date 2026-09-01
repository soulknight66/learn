'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadFactory, withServer } = require('./_helpers');

test('CommonJS export creates independent callable applications', () => {
  const createApplication = loadFactory();
  assert.equal(typeof createApplication, 'function');

  const first = createApplication();
  const second = createApplication();
  assert.equal(typeof first, 'function');
  assert.equal(typeof second, 'function');
  assert.notEqual(first, second);

  const methodNames = [
    'use', 'get', 'post', 'put', 'patch', 'delete', 'options', 'head',
    'all', 'listen', 'handle'
  ];
  for (const name of methodNames) {
    assert.equal(typeof first[name], 'function', `app.${name} must be a function`);
  }
});

test('registration methods are chainable', () => {
  const app = loadFactory()();
  const noop = (_req, _res, next) => next();

  assert.equal(app.use(noop), app);
  for (const name of [
    'get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'all'
  ]) {
    assert.equal(app[name]('/shape-check', noop), app, `${name} must return app`);
  }
});

test('an empty app listens and returns the deterministic 404', async () => {
  const app = loadFactory()();
  await withServer(app, async (request) => {
    const response = await request({ path: '/nothing?x=1' });
    assert.equal(response.status, 404);
    assert.equal(response.body, 'Not Found');
    assert.equal(response.headers['content-type'], 'text/plain; charset=utf-8');
  });
});

