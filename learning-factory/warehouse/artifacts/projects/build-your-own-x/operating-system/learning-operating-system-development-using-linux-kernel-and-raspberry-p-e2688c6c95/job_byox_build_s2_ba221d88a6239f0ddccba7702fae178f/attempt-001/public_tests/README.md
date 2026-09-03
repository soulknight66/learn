# Public tests

`test_public.c` checks initialization, a short scheduling trace, common
rejections, one translation with permissions, and RAM-file gap semantics. It
is intentionally finite and is not a substitute for the complete contract.

Run it through `make -C starter test`. The initial TODO scaffold should compile
but only the initializer check should pass. Do not edit the test to accommodate
an implementation; investigate the implementation or reconcile it with
`REQUIREMENTS.md`.

Independent validation may vary operation order, use every slot and boundary,
inspect state after errors, and compile the same API in a freestanding build.
