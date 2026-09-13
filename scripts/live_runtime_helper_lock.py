#!/usr/bin/env python3

from __future__ import annotations

import contextlib
import fcntl
import os
from pathlib import Path
from typing import Iterator


def helper_lock_path() -> Path:
    return Path(os.environ.get("MESHCORE_PI_HELPER_LOCK_PATH", "/tmp/meshcore-pi-helper.lock"))


@contextlib.contextmanager
def exclusive_helper_lock() -> Iterator[None]:
    path = helper_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch(mode=0o666)
    try:
        os.chmod(path, 0o666)
    except PermissionError:
        pass
    with open(path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)