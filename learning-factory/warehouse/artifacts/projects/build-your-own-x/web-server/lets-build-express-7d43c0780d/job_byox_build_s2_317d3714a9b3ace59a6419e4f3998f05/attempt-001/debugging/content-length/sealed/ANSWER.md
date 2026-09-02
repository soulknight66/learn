# Diagnosis

`String.prototype.length` counts UTF-16 code units, while HTTP `Content-Length` counts payload
octets. `café` has four JavaScript code units but five bytes in UTF-8, so the header is too small.

The minimal correction is:

```js
res.setHeader('content-length', String(Buffer.byteLength(text, 'utf8')));
```

A regression test should assert the header value `5`, decode the complete body as UTF-8, and close
the ephemeral server in `finally`.
