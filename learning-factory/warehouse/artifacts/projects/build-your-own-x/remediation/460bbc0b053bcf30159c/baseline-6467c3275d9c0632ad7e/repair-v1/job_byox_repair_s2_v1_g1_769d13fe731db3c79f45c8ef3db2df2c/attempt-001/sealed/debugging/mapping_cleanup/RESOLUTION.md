# Mapping cleanup resolution

Each mapping exists in two ownership views. Exit must set every referenced `frame_owner[frame]` to -1
and clear the corresponding process mapping before marking the process exited. Validate all frame
indices/owners first so corruption cannot produce half a cleanup. The regression should map at least
two non-adjacent frames, exit, then map both frames into another live process.
