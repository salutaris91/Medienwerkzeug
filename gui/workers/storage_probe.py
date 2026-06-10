"""Standalone storage measurement probe (Roadmap #16).

Executed as a separate process via ``python storage_probe.py <mode> <path>``
so that a stale network mount can only hang this process. The parent kills it
with SIGKILL after a timeout — threads stuck in uninterruptible sleep (state
"D") cannot be killed and would accumulate in the main process.

Must stay free of project imports: the process is started fresh every cycle,
so importing application modules would be slow and could trigger side effects
(settings loading, worker threads). The ``folder_size`` walk mirrors
``gui.core.helpers.get_folder_size_bytes``.

Output: one JSON object on stdout. Errors go to stderr with exit code 1;
the parent process logs them.
"""
import json
import os
import shutil
import sys


def measure_folder_size_bytes(path):
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for name in filenames:
            file_path = os.path.join(dirpath, name)
            try:
                if not os.path.islink(file_path):
                    total += os.path.getsize(file_path)
            except OSError:
                pass
    return {"bytes": total}


def measure_disk_usage(path):
    if not os.path.exists(path):
        return {"exists": False}
    usage = shutil.disk_usage(path)
    return {
        "exists": True,
        "total": usage.total,
        "used": usage.used,
        "free": usage.free,
    }


def main(argv):
    if len(argv) != 2 or argv[0] not in ("folder_size", "disk_usage"):
        print("usage: storage_probe.py {folder_size|disk_usage} <path>", file=sys.stderr)
        return 2
    mode, path = argv
    try:
        if mode == "folder_size":
            result = measure_folder_size_bytes(path)
        else:
            result = measure_disk_usage(path)
    except Exception as e:
        print(f"storage probe failed ({mode} for {path}): {e}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
