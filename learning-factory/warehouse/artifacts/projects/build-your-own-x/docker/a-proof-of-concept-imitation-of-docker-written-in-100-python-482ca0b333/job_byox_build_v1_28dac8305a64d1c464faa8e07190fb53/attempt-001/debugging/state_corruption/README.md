# Exercise: duplicate RUNNING claims

Two workers each execute a `SELECT state` using one connection. Both see `CREATED`. Each later opens a new connection and executes `UPDATE containers SET state='RUNNING'`. The event table contains two claim events, but only one payload should exist.

Questions:

1. Why does checking the state in Python not establish ownership?
2. Where should the transaction begin, and which SQLite transaction mode is appropriate?
3. What expected-state check and database constraint would make a stale claimant fail?
4. What should happen to event insertion when the state update fails?
