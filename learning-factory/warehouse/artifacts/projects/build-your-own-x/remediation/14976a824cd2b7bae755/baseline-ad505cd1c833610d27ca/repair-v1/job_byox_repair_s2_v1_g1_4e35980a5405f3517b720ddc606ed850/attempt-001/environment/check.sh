#!/usr/bin/env bash
set -u

missing=0
for tool in bash chroot cp hostname mkdir mktemp mount mv rm sort; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf 'AVAILABLE %s\n' "$tool"
    else
        printf 'MISSING %s\n' "$tool"
        missing=1
    fi
done

if command -v unshare >/dev/null 2>&1; then
    printf 'AVAILABLE unshare\n'
    temp_parent=${TMPDIR:-.}
    [ -d "$temp_parent" ] && [ -w "$temp_parent" ] || temp_parent=.
    probe_dir=$(mktemp -d "$temp_parent/tinybox-probe.XXXXXX") || exit 1
    if unshare --user --map-root-user true >"$probe_dir/stdout" 2>"$probe_dir/stderr"; then
        printf 'SUPPORTED unprivileged-user-namespace\n'
    else
        printf 'BLOCKED unprivileged-user-namespace\n'
        if [ -s "$probe_dir/stderr" ]; then
            sed 's/^/DETAIL /' "$probe_dir/stderr"
        fi
    fi
    rm -rf -- "$probe_dir"
else
    printf 'MISSING unshare\n'
fi

exit "$missing"
