# Mistakes and risks

The first design sketch conflated writable sharing with copy-on-write. The corrected design
carries an explicit `shared` bit. Remaining limitations include modeling only one-page named
segments and serializing all operations with one lock.
