'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');

const createApplication = require('../reference/src');
const { request, withServer } = require('./helpers');

test('status(), set(), type(), json(), and send() are chainable and deterministic', async () => {
  const app = createApplication();
  app.get('/json', (req, res) => {
    assert.equal(res.status(201), res);
    assert.equal(res.set({ 'X-One': 1, 'X-Two': 'two' }), res);
    assert.equal(res.json({ ok: true }), res);
  });
  app.get('/html', (req, res) => {
    assert.equal(res.type('.html'), res);
    res.send('<p>hello</p>');
  });
  app.get('/custom', (req, res) => res.type('application/vnd.example+json').send('{}'));
  app.get('/literal-type', (req, res) => res.type('text/x-example').send('example'));

  await withServer(app, async (server) => {
    const json = await request(server, { path: '/json' });
    assert.equal(json.statusCode, 201);
    assert.equal(json.headers['x-one'], '1');
    assert.equal(json.headers['x-two'], 'two');
    assert.equal(json.headers['content-type'], 'application/json; charset=utf-8');
    assert.equal(json.headers['content-length'], '11');
    assert.equal(json.body, '{"ok":true}');

    const html = await request(server, { path: '/html' });
    assert.equal(html.headers['content-type'], 'text/html; charset=utf-8');
    assert.equal(html.body, '<p>hello</p>');

    const custom = await request(server, { path: '/custom' });
    assert.equal(custom.headers['content-type'], 'application/vnd.example+json');

    const literalType = await request(server, { path: '/literal-type' });
    assert.equal(literalType.headers['content-type'], 'text/x-example');
  });
});

test('send() handles buffers, typed arrays, objects, and empty values', async () => {
  const app = createApplication();
  app.get('/buffer', (req, res) => res.send(Buffer.from([0, 1, 2, 255])));
  app.get('/typed', (req, res) => res.send(new Uint8Array([3, 4, 5])));
  app.get('/object', (req, res) => res.send({ value: 7 }));
  app.get('/empty', (req, res) => res.send());

  await withServer(app, async (server) => {
    const buffer = await request(server, { path: '/buffer' });
    assert.equal(buffer.headers['content-type'], 'application/octet-stream');
    assert.deepEqual([...buffer.buffer], [0, 1, 2, 255]);

    const typed = await request(server, { path: '/typed' });
    assert.deepEqual([...typed.buffer], [3, 4, 5]);
    assert.deepEqual(JSON.parse((await request(server, { path: '/object' })).body), { value: 7 });

    const empty = await request(server, { path: '/empty' });
    assert.equal(empty.headers['content-length'], '0');
    assert.equal(empty.body, '');
  });
});

test('204 and 304 preserve content type while suppressing framing and body bytes', async () => {
  const app = createApplication();
  app.get('/no-content', (req, res) => res.status(204).type('text').send('ignored'));
  app.get('/not-modified', (req, res) => res.status(304).json({ ignored: true }));

  await withServer(app, async (server) => {
    const noContent = await request(server, { path: '/no-content' });
    assert.equal(noContent.body, '');
    assert.equal(noContent.headers['content-type'], 'text/plain; charset=utf-8');
    assert.equal(noContent.headers['content-length'], undefined);

    const notModified = await request(server, { path: '/not-modified' });
    assert.equal(notModified.body, '');
    assert.equal(notModified.headers['content-type'], 'application/json; charset=utf-8');
    assert.equal(notModified.headers['content-length'], undefined);
  });
});

test('404 and 500 defaults have stable status, body, type, and length', async () => {
  const app = createApplication();
  app.get('/throw', () => {
    throw new Error('secret stack detail');
  });
  app.get('/next-error', (req, res, next) => next('also secret'));

  await withServer(app, async (server) => {
    const missing = await request(server, { path: '/missing' });
    assert.equal(missing.statusCode, 404);
    assert.equal(missing.headers['content-type'], 'text/plain; charset=utf-8');
    assert.equal(missing.headers['content-length'], '9');
    assert.equal(missing.body, 'Not Found');

    for (const path of ['/throw', '/next-error']) {
      const failed = await request(server, { path });
      assert.equal(failed.statusCode, 500);
      assert.equal(failed.headers['content-type'], 'text/plain; charset=utf-8');
      assert.equal(failed.headers['content-length'], '21');
      assert.equal(failed.body, 'Internal Server Error');
    }
  });
});

test('serialization and helper validation failures flow to the deterministic 500', async () => {
  const app = createApplication();
  app.get('/circular', (req, res) => {
    const value = {};
    value.self = value;
    res.json(value);
  });
  app.get('/bad-status', (req, res) => res.status(99).send('never'));
  app.get('/undefined-header', (req, res) => res.set('X-Bad', undefined).send('never'));
  app.get('/null-header', (req, res) => res.set('X-Null', null).send('accepted'));

  await withServer(app, async (server) => {
    for (const path of ['/circular', '/bad-status', '/undefined-header']) {
      const response = await request(server, { path });
      assert.equal(response.statusCode, 500);
      assert.equal(response.body, 'Internal Server Error');
    }

    const nullHeader = await request(server, { path: '/null-header' });
    assert.equal(nullHeader.statusCode, 200);
    assert.equal(nullHeader.headers['x-null'], 'null');
    assert.equal(nullHeader.body, 'accepted');
  });
});

test('GET and HEAD are separate methods and HEAD defaults suppress bytes', async () => {
  const app = createApplication();
  app.get('/from-get', (req, res) => res.set('X-Source', 'get').send('abcdef'));

  await withServer(app, async (server) => {
    const response = await request(server, { method: 'HEAD', path: '/from-get' });
    assert.equal(response.statusCode, 404);
    assert.equal(response.headers['x-source'], undefined);
    assert.equal(response.headers['content-length'], '9');
    assert.equal(response.body, '');
  });
});

test('an explicit HEAD route is independent from GET', async () => {
  const app = createApplication();
  app.get('/resource', (req, res) => res.set('X-Source', 'get').send('get'));
  app.head('/resource', (req, res) => res.set('X-Source', 'head').send('head-body'));

  await withServer(app, async (server) => {
    const head = await request(server, { method: 'HEAD', path: '/resource' });
    assert.equal(head.headers['x-source'], 'head');
    assert.equal(head.headers['content-length'], '9');
    assert.equal(head.body, '');

    const get = await request(server, { path: '/resource' });
    assert.equal(get.headers['x-source'], 'get');
    assert.equal(get.body, 'get');
  });
});

test('HEAD suppresses a body written without response helpers at the HTTP layer', async () => {
  const app = createApplication();
  app.head('/raw', (req, res) => {
    res.setHeader('Content-Length', '8');
    res.end('raw-body');
  });

  await withServer(app, async (server) => {
    const response = await request(server, { method: 'HEAD', path: '/raw' });
    assert.equal(response.statusCode, 200);
    assert.equal(response.headers['content-length'], '8');
    assert.equal(response.body, '');
  });
});
