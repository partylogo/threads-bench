"""Shared persistence helpers honoring `templates/FAILSAFE.md`.

Every script that mutates a destructive-writes file (per FAILSAFE) must
go through `atomic_write_json` instead of bare `open("w") + json.dump`.
The contract is:

1. Copy current file to ``<path>.bak-<ISO>`` (skipped if file is new).
2. Write new content to ``<path>.tmp-<ISO>``.
3. ``os.replace`` ``<path>.tmp-<ISO>`` over ``<path>`` (atomic commit).
4. Prune ``<path>.bak-*`` to the most recent ``keep`` (default 5).

If steps 1-2 fail, the user's data is unchanged because the atomic
rename has not happened. If the rename itself fails (Windows: another
process is holding the file open), retry with backoff, then raise with
the new content preserved as ``<path>.tmp-FAILED-<ISO>`` so the user can
recover.

Stdlib only (``json`` / ``os`` / ``shutil`` / ``time``); no new
dependency.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Union


PathLike = Union[str, os.PathLike]

ISO_BAK_FORMAT = "%Y%m%dT%H%M%SZ"


def configure_utf8_stdout() -> None:
    """Reconfigure ``sys.stdout`` / ``sys.stderr`` to UTF-8.

    Call once at the top of every CLI ``main()`` before any ``print``.
    On Windows the default cp950 / cp1252 console raises
    ``UnicodeEncodeError`` on the first CJK character, which aborts a
    refresh / fetch run mid-loop.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, OSError, ValueError):
                # best-effort: some stream wrappers reject reconfigure
                pass


def _iso_stamp() -> str:
    return datetime.now(timezone.utc).strftime(ISO_BAK_FORMAT)


def _list_backups(path: Path) -> List[Path]:
    """Return existing ``<name>.bak-*`` siblings sorted oldest first."""
    parent = path.parent if path.parent != Path("") else Path(".")
    pattern = f"{path.name}.bak-*"
    return sorted(parent.glob(pattern))


def prune_backups(path: PathLike, keep: int = 5) -> int:
    """Delete oldest ``.bak-*`` files past the ``keep`` window.

    Returns the number of backups deleted. Best-effort: a single delete
    failure does not abort the rest. Never deletes the destination file
    itself.
    """
    target = Path(path)
    backups = _list_backups(target)
    if len(backups) <= keep:
        return 0
    deleted = 0
    for old in backups[: len(backups) - keep]:
        try:
            old.unlink()
            deleted += 1
        except OSError:
            pass
    return deleted


def backup_file(path: PathLike, *, stamp: Optional[str] = None) -> Optional[Path]:
    """Copy ``path`` to ``<path>.bak-<ISO>`` and return the backup path.

    Returns ``None`` when the file does not exist yet (nothing to back
    up — a first write is not destructive). Raises whatever
    ``shutil.copy2`` raises on failure; callers under FAILSAFE must
    treat that as "abort, do not write".

    Split out of ``atomic_write_json`` so a multi-file write can back up
    every target *before* committing any of them, per the multi-file
    clause in ``templates/FAILSAFE.md``.
    """
    target = Path(path)
    if not target.exists():
        return None
    bak = target.with_name(f"{target.name}.bak-{stamp or _iso_stamp()}")
    shutil.copy2(target, bak)
    return bak


def _atomic_replace(
    target: Path,
    render: Any,
    *,
    backup: bool,
    keep: int,
    rename_retries: int,
    rename_backoff: float,
    stamp: Optional[str] = None,
) -> None:
    """Shared body of ``atomic_write_json`` / ``atomic_write_text``.

    ``render`` is called with the open temp-file handle and writes the
    payload. Everything else — backup, fsync, retrying rename, keeping
    the new content as ``.tmp-FAILED-<ISO>`` on give-up, pruning — is
    identical between the two formats and lives here so the two public
    functions cannot drift apart.
    """
    parent = target.parent
    if str(parent) and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)

    stamp = stamp or _iso_stamp()
    tmp = target.with_name(f"{target.name}.tmp-{stamp}")

    if backup:
        backup_file(target, stamp=stamp)

    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            render(fh)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except (AttributeError, OSError):
                # filesystems that do not support fsync (e.g. some FUSE
                # mounts) — skip; data integrity is best-effort.
                pass

        last_exc: Optional[BaseException] = None
        for attempt in range(rename_retries):
            try:
                os.replace(tmp, target)
                last_exc = None
                break
            except (PermissionError, OSError) as exc:
                last_exc = exc
                time.sleep(rename_backoff * (2 ** attempt))
        if last_exc is not None:
            failed = target.with_name(f"{target.name}.tmp-FAILED-{stamp}")
            try:
                tmp.rename(failed)
            except OSError:
                failed = tmp  # could not rename, original tmp path
            raise RuntimeError(
                f"atomic rename failed for {target} after {rename_retries} "
                f"attempts; new content preserved as {failed}; existing "
                f"file untouched."
            ) from last_exc
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass

    if backup:
        prune_backups(target, keep=keep)


def atomic_write_json(
    path: PathLike,
    obj: Any,
    *,
    backup: bool = True,
    keep: int = 5,
    indent: int = 2,
    rename_retries: int = 5,
    rename_backoff: float = 0.2,
) -> None:
    """Write ``obj`` as JSON to ``path`` per the FAILSAFE contract.

    Args:
        path: Destination file. Parent dirs are created if missing.
        obj: JSON-serialisable Python object.
        backup: When True (default) and the file already exists, copy it
            to ``<path>.bak-<ISO>`` before writing.
        keep: Maximum ``.bak-*`` files to keep (default 5). Older
            backups are pruned after a successful rename.
        indent: ``json.dump`` indent argument.
        rename_retries: Retry count for the atomic rename. Windows can
            transiently fail when the file is open in another process.
        rename_backoff: Initial backoff in seconds; doubles per retry.

    Raises:
        RuntimeError: If the atomic rename fails after retries. The new
            content is preserved as ``<path>.tmp-FAILED-<ISO>`` and the
            existing file is left untouched.
    """
    _atomic_replace(
        Path(path),
        lambda fh: json.dump(obj, fh, ensure_ascii=False, indent=indent),
        backup=backup,
        keep=keep,
        rename_retries=rename_retries,
        rename_backoff=rename_backoff,
    )


def atomic_write_text(
    path: PathLike,
    text: str,
    *,
    backup: bool = True,
    keep: int = 5,
    rename_retries: int = 5,
    rename_backoff: float = 0.2,
) -> None:
    """Write ``text`` to ``path`` per the FAILSAFE contract.

    The markdown counterpart of ``atomic_write_json`` — same backup,
    same atomic rename, same pruning. Exists because half the files
    under the destructive-writes policy (``concept_library.md``,
    ``style_guide.md``, ``brand_voice.md``, ``drafts/*.md``) are plain
    text, and without this they had no safe writer at all.

    Args:
        path: Destination file. Parent dirs are created if missing.
        text: Full new content. Written UTF-8 with ``\\n`` line endings.
        backup: When True (default) and the file already exists, copy it
            to ``<path>.bak-<ISO>`` before writing.
        keep: Maximum ``.bak-*`` files to keep (default 5).
        rename_retries: Retry count for the atomic rename.
        rename_backoff: Initial backoff in seconds; doubles per retry.

    Raises:
        RuntimeError: If the atomic rename fails after retries. The new
            content is preserved as ``<path>.tmp-FAILED-<ISO>`` and the
            existing file is left untouched.
    """
    _atomic_replace(
        Path(path),
        lambda fh: fh.write(text),
        backup=backup,
        keep=keep,
        rename_retries=rename_retries,
        rename_backoff=rename_backoff,
    )


def parse_iso_or_min(value: Any) -> datetime:
    """Parse an ISO-8601 timestamp; fall back to ``datetime.min`` UTC.

    Handles ``Z`` and offset suffixes uniformly. Drop-in replacement for
    ``lambda p: p.get("created_at", "")`` sort keys, which compare ISO
    strings lexicographically and silently corrupt order when offsets
    differ (e.g. ``"+07:00"`` < ``"+00:00"`` < ``"Z"`` lexicographically
    but should compare equal chronologically).
    """
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def post_sort_key(post: dict) -> datetime:
    """Sort key for tracker post dicts using ISO-aware ``created_at``."""
    return parse_iso_or_min(post.get("created_at"))
