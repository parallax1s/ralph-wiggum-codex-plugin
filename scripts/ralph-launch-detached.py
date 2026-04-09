#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pid-file", required=True)
    parser.add_argument("--stdout-file", required=True)
    parser.add_argument("--stderr-file", required=True)
    parser.add_argument("--cwd")
    parser.add_argument("--alive-delay-ms", type=int, default=250)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.command or args.command[0] != "--" or len(args.command) < 2:
        parser.error("command must be provided after --")
    args.command = args.command[1:]
    return args


def main() -> int:
    args = _parse_args()
    stdout_path = Path(args.stdout_file)
    stderr_path = Path(args.stderr_file)
    pid_path = Path(args.pid_file)
    cwd = args.cwd or os.getcwd()

    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.parent.mkdir(parents=True, exist_ok=True)

    with open(stdout_path, "ab") as stdout_handle, open(stderr_path, "ab") as stderr_handle:
        child = subprocess.Popen(
            args.command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )

    time.sleep(max(0, args.alive_delay_ms) / 1000.0)
    if child.poll() is not None:
        return int(child.returncode or 1)

    pid_path.write_text(f"{child.pid}\n", encoding="utf-8")
    print(child.pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
