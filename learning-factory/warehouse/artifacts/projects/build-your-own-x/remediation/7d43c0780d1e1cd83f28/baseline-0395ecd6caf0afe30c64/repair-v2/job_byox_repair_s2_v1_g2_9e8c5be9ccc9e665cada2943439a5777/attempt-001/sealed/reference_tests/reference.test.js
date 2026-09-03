'use strict';

const assert = require('node:assert/strict');
const { PassThrough } = require('node:stream');
const test = require('node:test');
const tiny = require('../reference');
const { compose } = require('../reference/src/compose');
const {
  compilePattern,
  decodeCapture
} = require('../reference/src/router');
const {
  errorDetails,
  normalizePrefix,
  prefixMatches
} = require('../reference/src/application');
const { request, withServer } = require('../../public_tests/helpers');

test('compose preserves onion order and rejects a repeated continuation', async () => {
  const events = [];
  const run = compose([
    async (_req, _res, next) => {
      events.push('a:in');
      await next();
      events.push('a:out');
    },
    async (_req, _res, next) => {
      events.push('b:in');
      await next();
      events.push('b:out');
    }
  ], () => events.push('terminal'));

  await run({}, {});
  assert.deepEqual(events, ['a:in', 'b:in', 'terminal', 'b:out', 'a:out']);

  const broken = compose([
    async (_req, _res, next) => {
      await next();
      await next();
    }
  ]);
  await assert.rejects(broken({}, {}), /next\(\) called more than once/);
});

test('compiled patterns validate names, match literals, and decode captures', () => {
  const route = compilePattern('/files/:owner/*rest');
  const parameters = route.match('/files/a%20b/docs/x%2Fy/');
  assert.equal(Object.getPrototypeOf(parameters), null);
  assert.deepEqual({ ...parameters }, { owner: 'a b', rest: 'docs/x/y/' });
  assert.equal(route.match('/FILES/a/docs'), null);

  const emptyWildcard = compilePattern('/files/*rest').match('/files');
  assert.equal(emptyWildcard.rest, '');

  assert.throws(() => compilePattern('relative'), /beginning with/);
  assert.throws(() => compilePattern('/x/:bad-name'), /invalid route parameter/);
  assert.throws(() => compilePattern('/x/:id/:id'), /duplicate/);
  assert.throws(() => compilePattern('/x/*rest/more'), /final segment/);
  assert.throws(() => compilePattern('/x//y'), /empty segments/);
  assert.throws(() => decodeCapture('%ZZ'), (error) => error.status === 400);
});

test('middleware prefixes match only at slash boundaries', () => {
  assert.equal(normalizePrefix('/api///'), '/api');
  assert.equal(prefixMatches('/api', '/api'), true);
  assert.equal(prefixMatches('/api', '/api/users'), true);
  assert.equal(prefixMatches('/api', '/apricot'), false);
  assert.equal(prefixMatches('/', '/anything'), true);
});

test('a delegated route restores its parameters around a later route', async () => {
  const app = tiny();
  const observations = [];

  app.get('/things/:first', async (req, _res, next) => {
    observations.push(`first-before:${req.params.first}`);
    await next();
    observations.push(`first-after:${req.params.first}`);
  });
  app.get('/things/:second', (req, res) => {
    observations.push(`second:${req.params.second}`);
    res.send('done');
  });

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/things/value' });
    assert.equal(response.status, 200);
    assert.equal(response.text, 'done');
  });
  assert.deepEqual(observations, [
    'first-before:value',
    'second:value',
    'first-after:value'
  ]);
});

test('scoped middleware does not run for a shared string prefix', async () => {
  const app = tiny();
  let calls = 0;
  app.use('/api', async (_req, _res, next) => {
    calls += 1;
    await next();
  });
  app.get('/apricot', (_req, res) => res.send('fruit'));
  app.get('/api', (_req, res) => res.send('root'));

  await withServer(app, async (server) => {
    assert.equal((await request(server, { path: '/apricot' })).status, 200);
    assert.equal(calls, 0);
    assert.equal((await request(server, { path: '/api' })).status, 200);
    assert.equal(calls, 1);
  });
});

test('HEAD fallback reports UTF-8 byte length without payload bytes', async () => {
  const app = tiny();
  app.get('/word', (_req, res) => res.send('café'));

  await withServer(app, async (server) => {
    const response = await request(server, { method: 'HEAD', path: '/word' });
    assert.equal(response.status, 200);
    assert.equal(response.headers['content-length'], '5');
    assert.equal(response.headers['content-type'], 'text/plain; charset=utf-8');
    assert.equal(response.body.length, 0);
  });
});

test('bodyless status codes remove entity headers', async () => {
  const app = tiny();
  app.get('/empty', (_req, res) => {
    res.set('content-type', 'text/custom');
    res.set('content-encoding', 'gzip');
    res.set('transfer-encoding', 'chunked');
    res.status(204).send('must disappear');
  });

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/empty' });
    assert.equal(response.status, 204);
    assert.equal(response.headers['content-type'], undefined);
    assert.equal(response.headers['content-encoding'], undefined);
    assert.equal(response.headers['content-length'], undefined);
    assert.equal(response.headers['transfer-encoding'], undefined);
    assert.equal(response.body.length, 0);
  });
});

test('unexpected failures are hidden and operational client failures are exposed', async () => {
  const app = tiny();
  app.get('/bug', () => {
    throw new Error('database detail that must stay private');
  });
  app.get('/limited', () => {
    throw new tiny.HttpError(429, 'Slow down', {
      headers: {
        'retry-after': '3',
        'content-length': '999'
      }
    });
  });

  await withServer(app, async (server) => {
    const bug = await request(server, { path: '/bug' });
    assert.equal(bug.status, 500);
    assert.deepEqual(JSON.parse(bug.text), {
      error: { status: 500, message: 'Internal Server Error' }
    });
    assert.equal(bug.text.includes('database detail'), false);

    const limited = await request(server, { path: '/limited' });
    assert.equal(limited.status, 429);
    assert.equal(limited.headers['retry-after'], '3');
    assert.equal(limited.headers['content-length'], String(Buffer.byteLength(limited.text)));
    assert.deepEqual(JSON.parse(limited.text), {
      error: { status: 429, message: 'Slow down' }
    });
  });

  assert.deepEqual(errorDetails({ status: 503, message: 'secret' }), {
    status: 503,
    message: 'Internal Server Error'
  });
});

test('malformed request targets and encoded route parameters become 400', async () => {
  const app = tiny();
  app.get('/items/:id', (req, res) => res.send(req.params.id));

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/items/%ZZ' });
    assert.equal(response.status, 400);
    assert.equal(JSON.parse(response.text).error.status, 400);
  });
});

test('JSON middleware accepts suffix types, empty bodies, and chunked input', async () => {
  const app = tiny();
  app.use(tiny.json({ limit: 32 }));
  app.post('/body', (req, res) => res.json({ body: req.body }));

  await withServer(app, async (server) => {
    const suffix = await request(server, {
      method: 'POST',
      path: '/body',
      headers: { 'content-type': 'application/problem+json' },
      body: '42',
      omitContentLength: true
    });
    assert.deepEqual(JSON.parse(suffix.text), { body: 42 });

    const empty = await request(server, {
      method: 'POST',
      path: '/body',
      headers: { 'content-type': 'application/json' },
      body: ''
    });
    assert.deepEqual(JSON.parse(empty.text), { body: null });
  });
});

test('JSON middleware rejects declared and streamed over-limit bodies', async () => {
  const app = tiny();
  app.use(tiny.json({ limit: 4 }));
  app.post('/body', (req, res) => res.json(req.body));

  await withServer(app, async (server) => {
    const declared = await request(server, {
      method: 'POST',
      path: '/body',
      headers: { 'content-type': 'application/json' },
      body: '"12345"'
    });
    assert.equal(declared.status, 413);

    const streamed = await request(server, {
      method: 'POST',
      path: '/body',
      headers: { 'content-type': 'application/json' },
      body: '"12345"',
      omitContentLength: true
    });
    assert.equal(streamed.status, 413);
  });
});

test('JSON middleware rejects unsupported encodings without parsing', async () => {
  const app = tiny();
  app.use(tiny.json());
  app.post('/body', (_req, res) => res.send('unreachable'));

  await withServer(app, async (server) => {
    const response = await request(server, {
      method: 'POST',
      path: '/body',
      headers: {
        'content-type': 'application/json',
        'content-encoding': 'gzip'
      },
      body: '{}'
    });
    assert.equal(response.status, 415);
  });
});

test('JSON middleware reports synthetic stream abort and length mismatch', async () => {
  const parse = tiny.json({ limit: 32 });
  const aborted = new PassThrough();
  aborted.headers = {
    'content-type': 'application/json'
  };
  aborted.complete = false;
  const abortedResult = parse(aborted, {}, () => undefined);
  aborted.emit('aborted');
  await assert.rejects(abortedResult, (error) => error.code === 'BODY_ABORTED');

  const mismatched = new PassThrough();
  mismatched.headers = {
    'content-type': 'application/json',
    'content-length': '3'
  };
  mismatched.complete = true;
  const mismatchResult = parse(mismatched, {}, () => undefined);
  mismatched.end('{}');
  await assert.rejects(mismatchResult, (error) => error.code === 'CONTENT_LENGTH_MISMATCH');
});

test('a second response helper call is translated without a duplicate response', async () => {
  const app = tiny();
  app.get('/twice', (_req, res) => {
    res.send('first');
    assert.throws(() => res.send('second'), /already ended/);
  });

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/twice' });
    assert.equal(response.status, 200);
    assert.equal(response.text, 'first');
  });
});

test('app.listen returns a functioning server', async () => {
  const app = tiny();
  app.get('/health', (_req, res) => res.json({ ok: true }));
  const server = app.listen(0, '127.0.0.1');
  try {
    if (!server.listening) {
      await new Promise((resolve, reject) => {
        server.once('listening', resolve);
        server.once('error', reject);
      });
    }
    const response = await request(server, { path: '/health' });
    assert.equal(response.status, 200);
    assert.deepEqual(JSON.parse(response.text), { ok: true });
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});
