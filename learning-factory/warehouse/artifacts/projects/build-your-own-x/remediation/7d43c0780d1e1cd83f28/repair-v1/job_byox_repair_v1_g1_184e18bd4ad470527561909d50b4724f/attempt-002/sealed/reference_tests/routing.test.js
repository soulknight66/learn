'use strict';

const assert = require('node:assert/strict');
const http = require('node:http');
const test = require('node:test');

const createApplication = require('../reference/src');
const { request, withServer } = require('./helpers');

test('the application exposes the complete API and is a callable listener', async () => {
  const app = createApplication();
  assert.equal(typeof app, 'function');
  for (const name of [
    'use',
    'get',
    'post',
    'put',
    'patch',
    'delete',
    'options',
    'head',
    'all',
    'listen',
    'handle',
  ]) {
    assert.equal(typeof app[name], 'function', name);
  }

  assert.equal(app.get('/callable', (req, res) => res.send('yes')), app);
  await withServer(http.createServer(app), async (server) => {
    const response = await request(server, { path: '/callable' });
    assert.equal(response.statusCode, 200);
    assert.equal(response.body, 'yes');
  });
});

test('verb routes and all() select only the intended methods', async () => {
  const app = createApplication();
  const verbs = ['get', 'post', 'put', 'patch', 'delete', 'options'];
  for (const verb of verbs) {
    app[verb](`/${verb}`, (req, res) => res.set('X-Method', req.method).send(verb));
  }
  app.all('/any', (req, res) => res.send(req.method));

  await withServer(app, async (server) => {
    for (const verb of verbs) {
      const response = await request(server, { method: verb.toUpperCase(), path: `/${verb}` });
      assert.equal(response.statusCode, 200);
      assert.equal(response.headers['x-method'], verb.toUpperCase());
      assert.equal(response.body, verb);
    }

    const wrongMethod = await request(server, { method: 'POST', path: '/get' });
    assert.equal(wrongMethod.statusCode, 404);
    const anyMethod = await request(server, { method: 'PATCH', path: '/any' });
    assert.equal(anyMethod.body, 'PATCH');
  });
});

test('literal route text is regex-safe and route matching is exact', async () => {
  const app = createApplication();
  app.get('/literal/a.b+$', (req, res) => res.send('literal'));
  app.get('/trail/', (req, res) => res.send('slash'));

  await withServer(app, async (server) => {
    assert.equal((await request(server, { path: '/literal/a.b+$' })).body, 'literal');
    assert.equal((await request(server, { path: '/literal/axbZZ' })).statusCode, 404);
    assert.equal((await request(server, { path: '/trail/' })).body, 'slash');
    assert.equal((await request(server, { path: '/trail' })).statusCode, 404);
    assert.equal((await request(server, { path: '/trail/more' })).statusCode, 404);
  });
});

test('named parameters and a final wildcard decode safely', async () => {
  const app = createApplication();
  app.get('/users/:user/books/:book', (req, res) => res.json(req.params));
  app.get('/files/*', (req, res) => res.json(req.params));

  await withServer(app, async (server) => {
    const params = await request(server, {
      path: '/users/Ada%20Lovelace/books/chapter%2Fone',
    });
    assert.deepEqual(JSON.parse(params.body), {
      user: 'Ada Lovelace',
      book: 'chapter/one',
    });

    const wildcard = await request(server, { path: '/files/a%20b/part%202.txt' });
    assert.deepEqual(JSON.parse(wildcard.body), { 0: 'a b/part 2.txt' });
    const emptyWildcard = await request(server, { path: '/files/' });
    assert.deepEqual(JSON.parse(emptyWildcard.body), { 0: '' });
    assert.equal((await request(server, { path: '/files' })).statusCode, 404);
  });
});

test('a standalone wildcard captures the full raw pathname and leading double slashes stay path data', async () => {
  const app = createApplication();
  app.get('//host/path', (req, res) => {
    res.json({ originalUrl: req.originalUrl, path: req.path });
  });
  app.get('*', (req, res) => res.json(req.params));

  await withServer(app, async (server) => {
    const doubleSlash = await request(server, { path: '//host/path?x=1' });
    assert.deepEqual(JSON.parse(doubleSlash.body), {
      originalUrl: '//host/path?x=1',
      path: '//host/path',
    });

    const catchAll = await request(server, { path: '/any/depth' });
    assert.deepEqual(JSON.parse(catchAll.body), { 0: '/any/depth' });
  });
});

test('request URL decorations preserve raw paths and repeated query values', async () => {
  const app = createApplication();
  app.get('/inspect/:name', (req, res) => {
    res.json({
      originalUrl: req.originalUrl,
      path: req.path,
      query: req.query,
      params: req.params,
      queryPrototypeIsNull: Object.getPrototypeOf(req.query) === null,
      paramsPrototypeIsNull: Object.getPrototypeOf(req.params) === null,
    });
  });

  await withServer(app, async (server) => {
    const response = await request(server, {
      path: '/inspect/Ada%20L?tag=one&tag=two&empty=&plus=a+b&__proto__=safe',
    });
    assert.deepEqual(JSON.parse(response.body), {
      originalUrl: '/inspect/Ada%20L?tag=one&tag=two&empty=&plus=a+b&__proto__=safe',
      path: '/inspect/Ada%20L',
      query: {
        tag: ['one', 'two'],
        empty: '',
        plus: 'a b',
        ['__proto__']: 'safe',
      },
      params: { name: 'Ada L' },
      queryPrototypeIsNull: false,
      paramsPrototypeIsNull: false,
    });
  });
});

test('use() matches prefixes only on segment boundaries', async () => {
  const app = createApplication();
  app.use('/api', (req, res, next) => {
    req.hitApi = true;
    next();
  });
  app.all('*', (req, res) => res.json({ hitApi: Boolean(req.hitApi), path: req.path }));

  await withServer(app, async (server) => {
    assert.equal(JSON.parse((await request(server, { path: '/api' })).body).hitApi, true);
    assert.equal(JSON.parse((await request(server, { path: '/api/items' })).body).hitApi, true);
    assert.equal(JSON.parse((await request(server, { path: '/apix' })).body).hitApi, false);
    assert.equal(JSON.parse((await request(server, { path: '/api-v2' })).body).hitApi, false);
  });
});

test('nested handler arrays are flattened in order', async () => {
  const app = createApplication();
  let firstParams;
  const step = (name) => (req, res, next) => {
    req.steps = req.steps || [];
    req.steps.push(name);
    if (firstParams === undefined) {
      firstParams = req.params;
    } else {
      assert.equal(req.params, firstParams);
    }
    next();
  };
  app.get('/nested', [step('a'), [[step('b')], step('c')]], (req, res) => {
    res.json(req.steps);
  });

  await withServer(app, async (server) => {
    assert.deepEqual(JSON.parse((await request(server, { path: '/nested' })).body), [
      'a',
      'b',
      'c',
    ]);
  });
});

test('registration rejects invalid handlers and invalid path grammar atomically', async () => {
  const app = createApplication();
  const wouldRun = (req, res) => res.send('partially installed');

  assert.throws(() => app.get('/bad-handler', [wouldRun, [42]]), TypeError);
  assert.throws(() => app.use('/empty', [[]]), TypeError);
  assert.throws(() => app.use('*', wouldRun), TypeError);
  assert.throws(() => app.get('missing-slash', wouldRun), TypeError);
  assert.throws(() => app.get('/x/*/tail', wouldRun), TypeError);
  assert.throws(() => app.get('/x/pre*', wouldRun), TypeError);
  assert.throws(() => app.get('/x/:', wouldRun), TypeError);
  assert.throws(() => app.get('/x/:not-valid', wouldRun), TypeError);
  assert.throws(() => app.get('/x/:id/:id', wouldRun), TypeError);
  const cyclic = [];
  cyclic.push(cyclic);
  assert.throws(() => app.use(cyclic), /cyclic/);

  await withServer(app, async (server) => {
    assert.equal((await request(server, { path: '/bad-handler' })).statusCode, 404);
  });
});

test('valid special parameter names become safe own properties', async () => {
  const app = createApplication();
  app.get('/special/:__proto__', (req, res) => {
    res.json({
      params: req.params,
      prototypeIsObject: Object.getPrototypeOf(req.params) === Object.prototype,
      protoIsOwn: Object.prototype.hasOwnProperty.call(req.params, '__proto__'),
    });
  });

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/special/safe' });
    assert.deepEqual(JSON.parse(response.body), {
      params: {
        ['__proto__']: 'safe',
      },
      prototypeIsObject: true,
      protoIsOwn: true,
    });
  });
});

test('middleware paths are normalized literal prefixes, not route patterns', async () => {
  const app = createApplication();
  app.use('/api/', (req, res, next) => {
    req.normalized = true;
    next();
  });
  app.use('/deep///', (req, res, next) => {
    req.multipleSlashesStayedLiteral = true;
    next();
  });
  app.use('/literal/:id', (req, res, next) => {
    req.literalColon = true;
    next();
  });
  app.all('*', (req, res) => {
    res.json({
      normalized: Boolean(req.normalized),
      literalColon: Boolean(req.literalColon),
      multipleSlashesStayedLiteral: Boolean(req.multipleSlashesStayedLiteral),
    });
  });

  await withServer(app, async (server) => {
    assert.deepEqual(JSON.parse((await request(server, { path: '/api' })).body), {
      normalized: true,
      literalColon: false,
      multipleSlashesStayedLiteral: false,
    });
    assert.deepEqual(JSON.parse((await request(server, { path: '/api/child' })).body), {
      normalized: true,
      literalColon: false,
      multipleSlashesStayedLiteral: false,
    });
    assert.deepEqual(JSON.parse((await request(server, { path: '/literal/value' })).body), {
      normalized: false,
      literalColon: false,
      multipleSlashesStayedLiteral: false,
    });
    assert.deepEqual(JSON.parse((await request(server, { path: '/literal/:id/child' })).body), {
      normalized: false,
      literalColon: true,
      multipleSlashesStayedLiteral: false,
    });
    assert.deepEqual(JSON.parse((await request(server, { path: '/deep' })).body), {
      normalized: false,
      literalColon: false,
      multipleSlashesStayedLiteral: false,
    });
    assert.deepEqual(JSON.parse((await request(server, { path: '/deep//child' })).body), {
      normalized: false,
      literalColon: false,
      multipleSlashesStayedLiteral: true,
    });
  });
});

test('each matching registration replaces params while its own handlers share one object', async () => {
  const app = createApplication();
  let firstRouteParams;
  let middlewareParams;

  app.get('/item/:first', (req, res, next) => {
    firstRouteParams = req.params;
    req.saved = req.params.first;
    next();
  });
  app.use('/item', (req, res, next) => {
    middlewareParams = req.params;
    assert.deepEqual(req.params, {});
    next();
  });
  app.get(
    '/item/:second',
    (req, res, next) => {
      assert.notEqual(req.params, firstRouteParams);
      assert.notEqual(req.params, middlewareParams);
      req.secondRouteParams = req.params;
      next();
    },
    (req, res) => {
      res.json({
        saved: req.saved,
        current: req.params,
        sameWithinRegistration: req.params === req.secondRouteParams,
      });
    },
  );

  await withServer(app, async (server) => {
    assert.deepEqual(JSON.parse((await request(server, { path: '/item/value' })).body), {
      saved: 'value',
      current: { second: 'value' },
      sameWithinRegistration: true,
    });
  });
});

test('application instances have independent route stacks', async () => {
  const first = createApplication();
  const second = createApplication();
  first.get('/only-first', (req, res) => res.send('first'));

  await withServer(first, async (firstServer) => {
    await withServer(second, async (secondServer) => {
      assert.equal((await request(firstServer, { path: '/only-first' })).body, 'first');
      assert.equal((await request(secondServer, { path: '/only-first' })).statusCode, 404);
    });
  });
});

test('malformed percent encoding safely enters ordinary error dispatch', async () => {
  const app = createApplication();
  app.get('/value/:id', (req, res) => res.send(req.params.id));

  await withServer(app, async (server) => {
    const response = await request(server, { path: '/value/%E0%A4%A' });
    assert.equal(response.statusCode, 500);
    assert.equal(response.headers['content-type'], 'text/plain; charset=utf-8');
    assert.equal(response.headers['content-length'], '21');
    assert.equal(response.body, 'Internal Server Error');
  });
});

test('capture decoding failures reach route-local and later global error handlers', async () => {
  const app = createApplication();
  app.get(
    '/local/:id',
    (req, res) => res.send(req.params.id),
    (error, req, res, next) => {
      void next;
      res.status(422).json({
        name: error.name,
        params: req.params,
        paramsArePlain: Object.getPrototypeOf(req.params) === Object.prototype,
      });
    },
  );
  app.get('/global/:id', (req, res) => res.send(req.params.id));
  app.use((error, req, res, next) => {
    void req;
    void next;
    res.status(409).json({ name: error.name });
  });

  await withServer(app, async (server) => {
    const local = await request(server, { path: '/local/%ZZ' });
    assert.equal(local.statusCode, 422);
    assert.deepEqual(JSON.parse(local.body), {
      name: 'URIError',
      params: {},
      paramsArePlain: true,
    });

    const global = await request(server, { path: '/global/%ZZ' });
    assert.equal(global.statusCode, 409);
    assert.deepEqual(JSON.parse(global.body), { name: 'URIError' });
  });
});
