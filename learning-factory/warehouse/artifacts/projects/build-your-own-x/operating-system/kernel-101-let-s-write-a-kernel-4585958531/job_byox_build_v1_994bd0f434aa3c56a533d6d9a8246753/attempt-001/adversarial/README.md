# Adversarial validation notes

Independent validators should emphasize sequences, not only isolated happy paths:

- exhaust, partially free, and reallocate frames while checking the cached count;
- block or exit the running process at every cursor position, then verify cyclic order;
- attempt duplicate and invalid mappings at mapping-table and frame-pool boundaries;
- translate every byte offset at page edges under missing and extra permission requests;
- use maximum-length names, embedded-zero file data, zero-length files, undersized output buffers,
  full tables, unlink/recreate cycles, and null pointers where the contract defines behavior;
- snapshot structures before operations required to fail and compare them afterward.

Avoid relying on elapsed time, address-layout randomness, or host-specific signed-char behavior. This
directory contains no expected answers or validator secrets.
