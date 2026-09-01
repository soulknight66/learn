# Sealed design

The reference keeps one address-ordered doubly linked physical block list. Allocation selects
the first sufficient free block; headers are aligned, splits retain a minimum aligned payload,
and free coalesces both neighbors. This is compact and auditable but allocation is O(number of
blocks).

The best-fit alternative shares the topology and chooses the smallest sufficient block. It
may reduce some remainders yet scans the whole list and can leave numerous tiny holes. The
segregated alternative maintains ten intrusive free lists indexed by size in addition to the
physical list. Candidate lookup starts at the request class; every split, free, merge, and
resize updates bin membership. Its stronger `lf_check` cross-validates both topologies.

All three intentionally serialize through caller discipline and retain metadata inside the
writable arena. No architecture is presented as production-ready.
