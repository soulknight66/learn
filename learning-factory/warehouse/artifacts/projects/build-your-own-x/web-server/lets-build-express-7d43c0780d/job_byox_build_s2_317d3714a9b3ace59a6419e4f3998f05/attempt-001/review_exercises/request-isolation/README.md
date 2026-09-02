# Review: request parameter cache

Review `broken.js`. The author says the module-level variable avoids allocating an object for every
request because Node.js runs JavaScript on one thread.

Provide:

- a severity and concise finding;
- a two-request interleaving that triggers it;
- an integration test outline;
- a minimal safe redesign.
