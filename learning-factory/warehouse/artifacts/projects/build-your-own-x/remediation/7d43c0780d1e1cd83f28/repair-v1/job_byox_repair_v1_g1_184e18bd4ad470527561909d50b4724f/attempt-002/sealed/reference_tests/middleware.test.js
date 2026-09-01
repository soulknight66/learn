'use strict';

const assert = require('node:assert/strict');
const http = require('node:http');
const test = require('node:test');

const createApplication = require('../reference/src');
const { request, withServer } = require('./helpers');

test('normal middleware runs in registration order and error middleware is skipped', async () => {
  const app = createApplication();
  app.use((req, res, next) => {
    req.order = ['first'];
    next();
  });
  app.use((error, req, res, next) => {
    req.order.push(`unexpected:${error.message}`);
    next();
  });
  app.use((req, res, next) => {
    req.order.push('second');
    next();
  });
  app.get('/order', (req, res) => res.json(req.order));

  await withServer(app, async (server) => {
    assert.deepEqual(JSON.parse((await request(server, { path: '/order' })).body), [
      'first',
      'second',
    ]);
  });
});

test('next(error) switches to arity-four handlers and next() can recover', async () => {
  const app = createApplication();
  let skipped = 0;
  app.get('/recover', (req, res, next) => next(new Error('recoverable')));
  app.use((req, res, next) => {
    skipped += 1;
    next();
  });
  app.use((error, req, res, next) => {
    assert.equal(error.message, 'recoverable');
    req.recovered = true;
    next();
  });
  app.use((req, res) => res.json({ recovered: req.recovered }));

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/recover' });
    assert.equal(response.statusCode, 200);
    assert.deepEqual(JSON.parse(response.body), { recovered: true });
    assert.equal(skipped, 0);
  });
});

test('every non-nullish next value, including falsy values, enters error mode', async () => {
  const app = createApplication();
  app.get('/false', (req, res, next) => next(false));
  app.get('/zero', (req, res, next) => next(0));
  app.get('/empty', (req, res, next) => next(''));
  app.get('/null', (req, res, next) => next(null), (req, res) => res.send('normal'));
  app.use((error, req, res, next) => {
    res.json({ type: typeof error, value: String(error) });
  });

  await withServer(app, async (server) => {
    assert.deepEqual(JSON.parse((await request(server, { path: '/false' })).body), {
      type: 'boolean',
      value: 'false',
    });
    assert.deepEqual(JSON.parse((await request(server, { path: '/zero' })).body), {
      type: 'number',
      value: '0',
    });
    assert.deepEqual(JSON.parse((await request(server, { path: '/empty' })).body), {
      type: 'string',
      value: '',
    });
    assert.equal((await request(server, { path: '/null' })).body, 'normal');
  });
});

test('synchronous throws reach error middleware without exposing the stack', async () => {
  const app = createApplication();
  app.get('/throw', () => {
    throw new Error('private detail');
  });
  app.use((error, req, res, next) => {
    assert.equal(error.message, 'private detail');
    res.status(422).send('handled');
  });

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/throw' });
    assert.equal(response.statusCode, 422);
    assert.equal(response.body, 'handled');
  });
});

test('rejected handler and error-handler promises propagate', async () => {
  const app = createApplication();
  app.get('/async-error', async () => {
    await Promise.resolve();
    throw new Error('first');
  });
  app.use(async (error, req, res, next) => {
    assert.equal(error.message, 'first');
    await Promise.resolve();
    throw new Error('second');
  });
  app.use((error, req, res, next) => {
    res.status(409).send(error.message);
  });

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/async-error' });
    assert.equal(response.statusCode, 409);
    assert.equal(response.body, 'second');
  });
});

test('thrown and rejected nullish reasons still enter error mode unchanged', async () => {
  const app = createApplication();
  app.get('/throw-null', () => {
    throw null;
  });
  app.get('/reject-undefined', () => Promise.reject(undefined));
  app.use((error, req, res, next) => {
    res.json({ isNull: error === null, isUndefined: error === undefined });
  });

  await withServer(app, async (server) => {
    assert.deepEqual(JSON.parse((await request(server, { path: '/throw-null' })).body), {
      isNull: true,
      isUndefined: false,
    });
    assert.deepEqual(JSON.parse((await request(server, { path: '/reject-undefined' })).body), {
      isNull: false,
      isUndefined: true,
    });
  });
});

test('callback-style asynchronous next() resumes dispatch', async () => {
  const app = createApplication();
  app.use((req, res, next) => {
    setImmediate(() => {
      req.fromTimer = true;
      next();
    });
  });
  app.get('/timer', (req, res) => res.json({ fromTimer: req.fromTimer }));

  await withServer(app, async (server) => {
    assert.deepEqual(JSON.parse((await request(server, { path: '/timer' })).body), {
      fromTimer: true,
    });
  });
});

test('calling one next callback twice cannot double-advance the stack', async () => {
  const app = createApplication();
  let visits = 0;
  app.use((req, res, next) => {
    next();
    next();
    setImmediate(next);
  });
  app.use((req, res, next) => {
    visits += 1;
    next();
  });
  app.get('/once', (req, res) => res.send(String(visits)));

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/once' });
    assert.equal(response.body, '1');
    await new Promise((resolve) => setImmediate(resolve));
    assert.equal(visits, 1);
  });
});

test('per-request params, query, and middleware state stay isolated under concurrency', async () => {
  const app = createApplication();
  const requestCount = 16;
  let arrivals = 0;
  let releaseBarrier;
  const barrier = new Promise((resolve) => {
    releaseBarrier = resolve;
  });
  app.use((req, res, next) => {
    req.local = { marker: req.query.marker };
    next();
  });
  app.get('/jobs/:id', async (req, res) => {
    const id = req.params.id;
    const marker = req.local.marker;
    arrivals += 1;
    if (arrivals === requestCount) {
      releaseBarrier();
    }
    await barrier;
    res.json({ id, marker, same: id === req.params.id && marker === req.local.marker });
  });

  await withServer(app, async (server) => {
    const pending = Array.from({ length: requestCount }, (_, index) =>
      request(server, {
        path: `/jobs/job-${index}?marker=m-${index}`,
      }),
    );
    const responses = await Promise.all(pending);
    for (let index = 0; index < responses.length; index += 1) {
      assert.deepEqual(JSON.parse(responses[index].body), {
        id: `job-${index}`,
        marker: `m-${index}`,
        same: true,
      });
    }
  });
});

test('handle() supports an outer completion callback', async () => {
  const app = createApplication();
  app.get('/inside', (req, res) => res.send('inside'));

  const outer = http.createServer((req, res) => {
    app.handle(req, res, (error) => {
      if (error) {
        res.statusCode = 502;
        res.end('outer error');
      } else {
        res.statusCode = 418;
        res.end('outer fallback');
      }
    });
  });

  await withServer(outer, async (server) => {
    assert.equal((await request(server, { path: '/inside' })).body, 'inside');
    const missing = await request(server, { path: '/outside' });
    assert.equal(missing.statusCode, 418);
    assert.equal(missing.body, 'outer fallback');
  });
});

test('a malformed escape can be observed as a URIError by error middleware', async () => {
  const app = createApplication();
  app.get('/bad/:value', (req, res) => res.send(req.params.value));
  app.use((error, req, res, next) => {
    res.status(422).json({ name: error.name });
  });

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/bad/%FF' });
    assert.equal(response.statusCode, 422);
    assert.deepEqual(JSON.parse(response.body), { name: 'URIError' });
  });
});
