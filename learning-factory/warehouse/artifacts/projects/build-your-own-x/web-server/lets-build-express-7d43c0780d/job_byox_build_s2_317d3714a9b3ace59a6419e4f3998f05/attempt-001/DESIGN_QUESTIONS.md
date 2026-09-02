# Design questions

Write down your decisions before implementation. These prompts have multiple defensible answers, but
your code should make one consistent choice that satisfies `REQUIREMENTS.md`.

1. What object owns the ordered layer list, and how will a layer distinguish prefix middleware from
   a method-and-pattern route?
2. Where is the “next called twice” invariant enforced when route handlers have their own nested
   sequence?
3. How will you calculate `Allow` without accidentally decoding parameters twice or mutating the
   request?
4. At what exact point are `req.params` and `req.routePattern` installed and restored?
5. Which response helper owns JSON serialization, default content type, body suppression, and byte
   length so those rules cannot diverge?
6. Which stream listeners does the JSON parser attach, and how are they removed on success, limit
   violation, error, and abort?
7. How will the request listener observe an asynchronous failure when `node:http` does not await an
   async callback?
8. What should happen if an error occurs after a handler has already written response bytes?
9. Which edge cases would expose shared state when two route handlers interleave?
