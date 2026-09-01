# License and provenance boundary

This challenge was independently authored from the general topic “build a
small container runtime.” It does not copy source code, prose, exercises, or
assets from the linked tutorial repository.

The catalog record that identified the topic comes from the Build Your Own X
catalog and is classified `CC0-1.0`. The catalog points to an upstream learning
resource, but that linked resource's license is recorded as `NOASSERTION`.
The link is provenance, not permission to reproduce its contents:

```text
https://github.com/Fewbytes/rubber-docker
```

Accordingly:

- no license grant for the linked resource is asserted here;
- no linked-resource content is included or required to solve Minibox;
- generated challenge material is independently created and licensed under
  the MIT terms in `LICENSE`; and
- anyone wishing to reuse upstream material must determine and follow its
  license separately.

Python, the Python standard library, the Linux kernel interfaces, and the
external `unshare` program are not redistributed by this repository. They
remain subject to their own licenses and host installation terms.

The immutable catalog snapshot and its identifiers are recorded separately in
`PROVENANCE.json`. That metadata does not expand the rights granted by any
linked project, and this boundary document does not claim endorsement by its
authors.

The phrase “for personal educational use” inside the immutable provenance
classification describes the generation context; it is not an additional
restriction on the MIT grant. Copyright and related rights in factory-injected
control files, staged `PRIOR_*` evidence, and the linked tutorial are outside
the scope of `LICENSE`.

`MANIFEST.yaml` uses `provenance_sha256` as the immutable catalog snapshot
identifier: it equals `PROVENANCE.json`'s internal `snapshot_sha256`. It is not
the hash of the provenance document's serialized bytes. The current immutable
document bytes hash to
`61d0f204e6e3a1e7647e3b6eed3a918b3a6b30ede1056213767ed030629a3cdc`.
Per-file generated-pack hashes and both meanings are recorded in
`sealed/production/ARTIFACT_INVENTORY.json`; its generator rejects unknown
top-level challenge entries and non-regular filesystem objects. Because the
authoritative manifest cannot gain another field, the inventory is not itself
anchored by the manifest and must be independently hashed or signed by a
release service before transfer.
