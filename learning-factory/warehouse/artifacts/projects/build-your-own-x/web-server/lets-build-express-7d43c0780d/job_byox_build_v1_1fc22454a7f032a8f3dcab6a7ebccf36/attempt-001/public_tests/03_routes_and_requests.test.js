'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadFactory, withServer } = require('./_helpers');

function sendJson(res, value) {
  res.setHeader('Content-Type', 'application/json');
  res.end(JSON.stringify(value));
}

test('literal routes match both method and the complete pathname', async () => {
  const app = loadFactory()();

  app.get('/resource', (_req, res) => res.end('get'));
  app.post('/resource', (_req, res) => res.end('post'));

  await withServer(app, async (request) => {
    assert.equal((await request({ method: 'GET', path: '/resource' })).body, 'get');
    assert.equal((await request({ method: 'POST', path: '/resource' })).body, 'post');
    assert.equal((await request({ method: 'GET', path: '/resource/' })).status, 404);
  });
});

test('params, originalUrl, path, and repeated query values are exposed', async () => {
  const app = loadFactory()();

  app.get('/users/:id', [
    (req, _res, next) => {
      req.firstHandlerId = req.params.id;
      next();
    },
    (req, res) => sendJson(res, {
      id: req.params.id,
      firstHandlerId: req.firstHandlerId,
      originalUrl: req.originalUrl,
      path: req.path,
      query: req.query
    })
  ]);

  await withServer(app, async (request) => {
    const response = await request({
      path: '/users/alice%20smith?tag=red&tag=blue&empty=&words=a+b'
    });
    assert.equal(response.status, 200);
    assert.deepEqual(JSON.parse(response.body), {
      id: 'alice smith',
      firstHandlerId: 'alice smith',
      originalUrl: '/users/alice%20smith?tag=red&tag=blue&empty=&words=a+b',
      path: '/users/alice%20smith',
      query: {
        tag: ['red', 'blue'],
        empty: '',
        words: 'a b'
      }
    });
  });
});

test('a final wildcard captures the remaining path', async () => {
  const app = loadFactory()();
  app.get('/files/*', (req, res) => sendJson(res, req.params));

  await withServer(app, async (request) => {
    const response = await request({ path: '/files/images/icons/logo.svg' });
    assert.equal(response.status, 200);
    assert.deepEqual(JSON.parse(response.body), { '0': 'images/icons/logo.svg' });
  });
});

test('all matches arbitrary methods while method-specific routes stay specific', async () => {
  const app = loadFactory()();

  app.get('/any', (_req, res) => res.end('get-only'));
  app.all('/any', (req, res) => res.end(`all:${req.method}`));

  await withServer(app, async (request) => {
    const get = await request({ method: 'GET', path: '/any' });
    const deletion = await request({ method: 'DELETE', path: '/any' });
    assert.equal(get.body, 'get-only');
    assert.equal(deletion.body, 'all:DELETE');
  });
});

test('middleware and routes share one registration order', async () => {
  const app = loadFactory()();

  app.use((req, _res, next) => {
    req.order = ['before'];
    next();
  });
  app.get('/ordered', (req, _res, next) => {
    req.order.push('route-one');
    next();
  });
  app.use('/ordered', (req, _res, next) => {
    req.order.push('between');
    next();
  });
  app.get('/ordered', (req, res) => {
    req.order.push('route-two');
    sendJson(res, req.order);
  });

  await withServer(app, async (request) => {
    const response = await request({ path: '/ordered' });
    assert.deepEqual(JSON.parse(response.body), [
      'before', 'route-one', 'between', 'route-two'
    ]);
  });
});
