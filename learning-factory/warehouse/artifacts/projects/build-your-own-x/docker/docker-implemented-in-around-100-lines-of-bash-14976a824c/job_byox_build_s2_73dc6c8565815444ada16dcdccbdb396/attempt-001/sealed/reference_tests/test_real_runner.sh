#!/usr/bin/env bash
set -u

repo_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
controller=$repo_root/sealed/reference/tinybox.sh
host_true=$(type -P true 2>/dev/null)
host_hostname=$(type -P hostname 2>/dev/null)
host_ps=$(type -P ps 2>/dev/null)

if [ -z "$host_true" ] || [ ! -f "$host_true" ] \
    || [ -z "$host_hostname" ] || [ ! -f "$host_hostname" ] \
    || [ -z "$host_ps" ] || [ ! -f "$host_ps" ]; then
    printf 'BLOCKED a host probe executable (true, hostname, or ps) is unavailable\n'
    exit 77
fi
if ! command -v ldd >/dev/null 2>&1; then
    printf 'BLOCKED ldd is unavailable; cannot construct the probe rootfs\n'
    exit 77
fi

temp_parent=${TMPDIR:-.}
[ -d "$temp_parent" ] && [ -w "$temp_parent" ] || temp_parent=.
test_root=$(mktemp -d "$temp_parent/tinybox-real-runner.XXXXXX") || exit 1
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM
rootfs=$test_root/rootfs
state=$test_root/state
dependency_list=$test_root/dependencies
: >"$dependency_list"
mkdir -p "$rootfs/proc" "$rootfs/tmp"
for executable in "$host_true" "$host_hostname" "$host_ps"; do
    mkdir -p "$rootfs$(dirname -- "$executable")"
    cp -L -- "$executable" "$rootfs$executable"
    ldd "$executable" | awk '{
        for (field = 1; field <= NF; field++) {
            if ($field ~ /^\//) print $field
        }
    }' >>"$dependency_list"
done
sort -u -o "$dependency_list" "$dependency_list"
while IFS= read -r dependency; do
    [ -f "$dependency" ] || continue
    mkdir -p "$rootfs$(dirname -- "$dependency")"
    cp -L -- "$dependency" "$rootfs$dependency"
done <"$dependency_list"

export TINYBOX_STATE_DIR=$state
unset TINYBOX_RUNNER
create_output=$(bash "$controller" create live "$rootfs" 2>&1)
create_status=$?
true_output=$(bash "$controller" run live -- "$host_true" 2>&1)
true_status=$?
hostname_output=$(bash "$controller" run live -- "$host_hostname" 2>&1)
hostname_status=$?
ps_output=$(bash "$controller" run live -- "$host_ps" -e -o 'pid=,comm=' 2>&1)
ps_status=$?
inspect_output=$(bash "$controller" inspect live 2>&1)
inspect_status=$?

printf 'CREATE_OUTPUT=%s\n' "$create_output"
printf 'CREATE_STATUS=%s\n' "$create_status"
printf 'TRUE_OUTPUT=%s\n' "$true_output"
printf 'TRUE_STATUS=%s\n' "$true_status"
printf 'HOSTNAME_OUTPUT=%s\n' "$hostname_output"
printf 'HOSTNAME_STATUS=%s\n' "$hostname_status"
printf 'PS_OUTPUT=%s\n' "$ps_output"
printf 'PS_STATUS=%s\n' "$ps_status"
printf 'INSPECT_STATUS=%s\n' "$inspect_status"
printf '%s\n' "$inspect_output"

expected=$(printf 'name=live\nstatus=EXITED\nexit_code=0')
if [ "$create_status" -eq 0 ] && [ "$create_output" = live ] \
    && [ "$true_status" -eq 0 ] && [ -z "$true_output" ] \
    && [ "$hostname_status" -eq 0 ] && [ "$hostname_output" = live ] \
    && [ "$ps_status" -eq 0 ] \
    && printf '%s\n' "$ps_output" | grep -Eq '^[[:space:]]*1[[:space:]]+ps[[:space:]]*$' \
    && [ "$inspect_status" -eq 0 ] && [ "$inspect_output" = "$expected" ]; then
    printf 'PASS real namespace runner completed the probe\n'
    exit 0
fi

printf 'BLOCKED real namespace runner did not complete the probe\n'
exit 77
