# REV-2 answer

The mapped data frame belongs to the caller, so freeing it in `unmap` is an
ownership violation and can double-free or free a foreign frame. Intermediate
tables may be shared by other leaves; a table is reclaimable only if it is empty
after its child entry is removed, cascading from level zero toward—but never
including—the root.

Before clearing the leaf, compute the complete reclamation set and verify that
the supplied allocator currently owns every table frame. Otherwise a late
deallocation error leaves a partial walk. Tests need an external data frame,
two leaves sharing each prefix depth, both unmap orders, a wrong allocator, and
allocator/table/translation snapshots around every failure.
