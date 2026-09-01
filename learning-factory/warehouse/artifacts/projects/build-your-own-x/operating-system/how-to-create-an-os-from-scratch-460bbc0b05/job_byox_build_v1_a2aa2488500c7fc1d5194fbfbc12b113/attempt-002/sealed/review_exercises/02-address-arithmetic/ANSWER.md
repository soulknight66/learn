# Address-arithmetic review findings

Translation splits the address only after proving it is below the modeled virtual address-space size.
That makes both the virtual-page index and page offset bounded. Page-table entries are checked for
presence, and their frame index is checked before indexing physical storage.

An alternative `offset + length <= capacity` check can wrap. This lab's byte APIs avoid that expression;
filesystem range checks use subtraction after first bounding the offset.
