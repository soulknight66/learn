'use strict';

const { Application } = require('./src/application');
const { json } = require('./src/body-json');
const { HttpError } = require('./src/http-error');

const APPLICATION_METHODS = [
  'use',
  'get',
  'post',
  'put',
  'patch',
  'delete',
  'head',
  'options',
  'listen'
];

function createApplication(options = {}) {
  const owner = new Application(options);
  const app = function applicationListener(req, res) {
    let pending;
    try {
      pending = Promise.resolve(owner.handle(req, res));
    } catch (error) {
      pending = Promise.reject(error);
    }
    void pending.catch((error) => {
      try {
        if (!res.headersSent && !res.writableEnded) {
          res.statusCode = 500;
          res.end();
        } else if (!res.destroyed) {
          res.destroy(error);
        }
      } catch (_ignored) {
        // The rejection is observed even if the transport can no longer report it.
      }
    });
    return pending;
  };

  for (const name of APPLICATION_METHODS) {
    app[name] = owner[name].bind(owner);
  }

  owner.publicApplication = app;
  return app;
}

module.exports = createApplication;
module.exports.createApplication = createApplication;
module.exports.json = json;
module.exports.HttpError = HttpError;
