#!/usr/bin/env bash
# fake_env records this path and exits before invoking it.  It still must be a
# valid executable because isolate.sh validates every configured host tool.
exit 99
