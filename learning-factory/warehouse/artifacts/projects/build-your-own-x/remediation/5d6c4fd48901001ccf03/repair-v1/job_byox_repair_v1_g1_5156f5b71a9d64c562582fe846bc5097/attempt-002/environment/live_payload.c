/* Benign payload for an explicitly opted-in namespace smoke test. */
#define _POSIX_C_SOURCE 200809L

#include <dirent.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

enum { MAX_PIDS = 128 };

static int namespace_identity(const char *name, char *output, size_t size) {
    char path[64];
    int length = snprintf(path, sizeof(path), "/proc/self/ns/%s", name);
    if (length < 0 || (size_t)length >= sizeof(path) || size < 2) {
        return 0;
    }
    ssize_t bytes = readlink(path, output, size - 1);
    if (bytes < 0 || (size_t)bytes >= size - 1) {
        return 0;
    }
    output[bytes] = '\0';
    return 1;
}

static int proc_mount_is_procfs(void) {
    FILE *stream = fopen("/proc/self/mountinfo", "r");
    char line[8192];
    int found = 0;
    if (stream == NULL) {
        return 0;
    }
    while (fgets(line, sizeof(line), stream) != NULL) {
        char mount_point[4096];
        char *separator = strstr(line, " - ");
        if (separator == NULL) {
            continue;
        }
        if (sscanf(line, "%*s %*s %*s %*s %4095s", mount_point) != 1) {
            continue;
        }
        if (strcmp(mount_point, "/proc") == 0 &&
                strncmp(separator, " - proc ", 8) == 0) {
            found = 1;
            break;
        }
    }
    (void)fclose(stream);
    return found;
}

static int decimal_name(const char *name) {
    const unsigned char *cursor = (const unsigned char *)name;
    if (*cursor == '\0') {
        return 0;
    }
    while (*cursor != '\0') {
        if (*cursor < (unsigned char)'0' || *cursor > (unsigned char)'9') {
            return 0;
        }
        cursor++;
    }
    return 1;
}

static int compare_long(const void *left, const void *right) {
    long first = *(const long *)left;
    long second = *(const long *)right;
    return (first > second) - (first < second);
}

static size_t visible_pids(long stored[MAX_PIDS], size_t *stored_count,
                           int *has_pid_one) {
    DIR *directory = opendir("/proc");
    struct dirent *entry;
    size_t total = 0;
    *stored_count = 0;
    *has_pid_one = 0;
    if (directory == NULL) {
        return 0;
    }
    while ((entry = readdir(directory)) != NULL) {
        char *end = NULL;
        long value;
        if (!decimal_name(entry->d_name)) {
            continue;
        }
        errno = 0;
        value = strtol(entry->d_name, &end, 10);
        if (errno != 0 || end == NULL || *end != '\0' || value <= 0) {
            continue;
        }
        if (value == 1) {
            *has_pid_one = 1;
        }
        if (*stored_count < MAX_PIDS) {
            stored[*stored_count] = value;
            (*stored_count)++;
        }
        total++;
    }
    (void)closedir(directory);
    qsort(stored, *stored_count, sizeof(stored[0]), compare_long);
    return total;
}

int main(void) {
    char hostname[64] = {0};
    char mount_namespace[128] = {0};
    char pid_namespace[128] = {0};
    char pid_text[2048] = {0};
    long pids[MAX_PIDS];
    size_t pid_count;
    size_t stored_count;
    size_t used = 0;
    int has_pid_one;
    int mount_namespace_ok = namespace_identity(
        "mnt", mount_namespace, sizeof(mount_namespace)
    );
    int pid_namespace_ok = namespace_identity(
        "pid", pid_namespace, sizeof(pid_namespace)
    );
    int hostname_ok = gethostname(hostname, sizeof(hostname) - 1) == 0;
    int pid_ok = getpid() == 1;
    int proc_ok = proc_mount_is_procfs();

    pid_count = visible_pids(pids, &stored_count, &has_pid_one);
    for (size_t index = 0; index < stored_count; index++) {
        int length = snprintf(
            pid_text + used,
            sizeof(pid_text) - used,
            "%s%ld",
            index == 0 ? "" : ",",
            pids[index]
        );
        if (length < 0 || (size_t)length >= sizeof(pid_text) - used) {
            break;
        }
        used += (size_t)length;
    }

    (void)printf(
        "pid=%ld\nhostname=%s\nproc_mount=%s\n"
        "proc_pid_count=%zu\nproc_pids=%s\nproc_pids_truncated=%s\n"
        "pid_namespace=%s\nmount_namespace=%s\n",
        (long)getpid(),
        hostname_ok ? hostname : "<error>",
        proc_ok ? "proc" : "missing-or-wrong-type",
        pid_count,
        stored_count == 0 ? "<none>" : pid_text,
        pid_count > stored_count ? "yes" : "no",
        pid_namespace_ok ? pid_namespace : "<error>",
        mount_namespace_ok ? mount_namespace : "<error>"
    );
    if (!hostname_ok || strcmp(hostname, "minibox") != 0 || !pid_ok ||
            !proc_ok || !has_pid_one || !pid_namespace_ok ||
            !mount_namespace_ok) {
        return 70;
    }
    return 17;
}
