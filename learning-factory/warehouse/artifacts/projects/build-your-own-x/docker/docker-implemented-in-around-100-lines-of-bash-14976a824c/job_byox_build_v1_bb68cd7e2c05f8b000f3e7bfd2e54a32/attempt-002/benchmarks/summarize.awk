BEGIN {
    FS = "\t"
    OFS = "\t"
}

NR == 1 {
    if ($1 != "iteration" || $2 != "operation" ||
            $3 != "duration_us" || $4 != "status") {
        print "summary: unexpected input header" > "/dev/stderr"
        exit 2
    }
    next
}

/^#/ || NF == 0 { next }

{
    if (NF != 4 || $1 !~ /^[0-9]+$/ || $3 !~ /^[0-9]+$/ ||
            $4 !~ /^[0-9]+$/) {
        print "summary: malformed sample at line " NR > "/dev/stderr"
        bad = 1
        next
    }
    if ($4 != 0) {
        print "summary: refusing failed sample at line " NR > "/dev/stderr"
        bad = 1
        next
    }
    operation = $2
    if (!(operation in seen)) {
        seen[operation] = 1
        order[++operations] = operation
        minimum[operation] = $3
        maximum[operation] = $3
    }
    count[operation]++
    total[operation] += $3
    if ($3 < minimum[operation]) minimum[operation] = $3
    if ($3 > maximum[operation]) maximum[operation] = $3
}

END {
    if (bad) exit 2
    if (operations == 0) {
        print "summary: no samples" > "/dev/stderr"
        exit 2
    }
    print "operation", "samples", "min_us", "mean_us", "max_us"
    for (idx = 1; idx <= operations; idx++) {
        operation = order[idx]
        printf "%s\t%d\t%d\t%.1f\t%d\n", operation, count[operation], \
            minimum[operation], total[operation] / count[operation], \
            maximum[operation]
    }
}
