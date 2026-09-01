# Content-addressed storage sketch

Hash compressed input bytes while copying them to an owned temporary file, fsync the file, verify the expected digest, then rename it under `blobs/sha256/<digest>`. Store image manifests as immutable mappings from an image ID/version to ordered layer digests. Materialization should use a separately journaled cache keyed by the manifest digest.

This avoids duplicate blobs and detects mutation between validation and provenance recording. It does not by itself solve safe unpacking, garbage-collection races, or atomic coordination with active containers. References and leases must be durable before a collector can remove an unreferenced blob.
