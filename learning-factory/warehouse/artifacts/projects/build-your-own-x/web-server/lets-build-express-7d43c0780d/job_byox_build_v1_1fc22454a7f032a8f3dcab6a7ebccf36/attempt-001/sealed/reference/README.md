# Mini Express reference

This directory contains the dependency-free CommonJS reference implementation. Import it with:

```js
const createApplication = require('./sealed/reference/src');
const app = createApplication();
```

From the repository root, run the complete reference suite with Node.js 18 or newer:

```bash
node --test sealed/reference_tests/*.test.js
```

No install step is required. As an alternative, `npm --prefix sealed/reference test` invokes the
same suite.

The router treats route paths as exact (including a trailing slash). A `use` mount is a path prefix
on a segment boundary. Parameter segments have the form `:name`; a wildcard must be the final,
complete segment and is available as `req.params[0]`. `req.path` remains percent-encoded while
captured parameters are decoded. Query values are decoded with `URLSearchParams`; a repeated key
becomes an array in encounter order. Both `req.query` and `req.params` are ordinary objects, with
special names such as `__proto__` installed as safe own data properties.

Named parameter identifiers use `[A-Za-z_][A-Za-z0-9_]*` and may not repeat within one route.

GET and HEAD are distinct route methods; there is no implicit GET fallback for HEAD. Passing any
non-nullish value to `next(value)` enters error mode.

Unhandled framework outcomes are stable UTF-8 text: `Not Found` (404) and `Internal Server Error`
(500), with no trailing newline. A malformed escape in a captured parameter enters ordinary error
dispatch and therefore uses the 500 default when no error middleware handles it. HEAD responses
retain the corresponding headers, including content length, but contain no bytes.
