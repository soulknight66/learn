# Root cause

`merge_next` recovers two header widths even though combining adjacent blocks removes exactly
one intervening header. The merged size therefore claims bytes beyond the next physical block,
corrupting the arena coverage invariant and enabling a later split/allocation to overlap
metadata or escape the arena. The patch restores `current payload + one header + next payload`.
