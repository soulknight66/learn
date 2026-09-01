'use strict';

const http = require('node:http');

const ROUTE_METHODS = [
  'get',
  'post',
  'put',
  'patch',
  'delete',
  'options',
  'head',
  'all'
];

/**
 * Create one independent mini application.
 *
 * This starter deliberately records registrations without dispatching them. It
 * is runnable so that API-shape and server-lifecycle work can be verified while
 * the routing engine is developed.
 */
function createApplication() {
  const layers = [];

  function app(req, res) {
    return app.handle(req, res);
  }

  app.use = function use(...args) {
    // TODO: validate/normalize the optional path and flatten handler arrays.
    layers.push({ kind: 'middleware', args: args.slice() });
    return app;
  };

  for (const method of ROUTE_METHODS) {
    app[method] = function registerRoute(...args) {
      // TODO: validate/compile the route and flatten handler arrays.
      layers.push({ kind: 'route', method, args: args.slice() });
      return app;
    };
  }

  app.handle = function handle(req, res) {
    // TODO: derive request fields and install response helpers.
    // TODO: dispatch matching layers with normal/error continuation state.
    void req;
    void layers;

    // This is the specified result for an application whose dispatch stack has
    // been exhausted. It also keeps the incomplete scaffold usable as a server.
    if (!res.writableEnded) {
      res.statusCode = 404;
      res.setHeader('Content-Type', 'text/plain; charset=utf-8');
      res.end(req.method === 'HEAD' ? undefined : 'Not Found');
    }
  };

  app.listen = function listen(...args) {
    const server = http.createServer(app);
    return server.listen(...args);
  };

  return app;
}

module.exports = createApplication;

