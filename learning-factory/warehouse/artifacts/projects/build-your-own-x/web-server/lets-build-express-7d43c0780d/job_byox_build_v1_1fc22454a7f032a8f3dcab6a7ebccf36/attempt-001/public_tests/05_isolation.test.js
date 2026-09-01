'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadFactory, withServer } = require('./_helpers');

test('concurrent requests keep params and query objects isolated', async () => {
  const app = loadFactory()();
  let arrivals = 0;
  let releaseBoth;
  const bothArrived = new Promise((resolve) => {
    releaseBoth = resolve;
  });

  app.get('/work/:id', async (req, res) => {
    const paramsReference = req.params;
    const queryReference = req.query;
    arrivals += 1;
    if (arrivals === 2) releaseBoth();
    await bothArrived;
    res.json({
      id: req.params.id,
      token: req.query.token,
      sameParamsObject: req.params === paramsReference,
      sameQueryObject: req.query === queryReference
    });
  });

  await withServer(app, async (request) => {
    const [slow, fast] = await Promise.all([
      request({ path: '/work/slow?token=alpha' }),
      request({ path: '/work/fast?token=beta' })
    ]);

    assert.deepEqual(JSON.parse(slow.body), {
      id: 'slow',
      token: 'alpha',
      sameParamsObject: true,
      sameQueryObject: true
    });
    assert.deepEqual(JSON.parse(fast.body), {
      id: 'fast',
      token: 'beta',
      sameParamsObject: true,
      sameQueryObject: true
    });
  });
});

test('each matching route replaces params instead of retaining old names', async () => {
  const app = loadFactory()();

  app.get('/item/:first', (req, _res, next) => {
    req.firstCapture = req.params.first;
    next();
  });
  app.get('/item/:second', (req, res) => {
    res.json({ firstCapture: req.firstCapture, current: req.params });
  });

  await withServer(app, async (request) => {
    const response = await request({ path: '/item/value' });
    assert.deepEqual(JSON.parse(response.body), {
      firstCapture: 'value',
      current: { second: 'value' }
    });
  });
});

test('separate application instances do not share registrations', async () => {
  const createApplication = loadFactory();
  const first = createApplication();
  const second = createApplication();

  first.get('/only-first', (_req, res) => res.send('first'));

  await withServer(first, async (requestFirst) => {
    await withServer(second, async (requestSecond) => {
      const present = await requestFirst({ path: '/only-first' });
      const absent = await requestSecond({ path: '/only-first' });
      assert.equal(present.status, 200);
      assert.equal(present.body, 'first');
      assert.equal(absent.status, 404);
      assert.equal(absent.body, 'Not Found');
    });
  });
});
