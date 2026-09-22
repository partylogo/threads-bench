#!/usr/bin/env python3
"""Commit prepared files into place under the FAILSAFE write policy.

Why this exists
---------------
``templates/FAILSAFE.md`` requires every destructive write to back the
target up to ``<file>.bak-<ISO>`` first. Spelled out as a shell command
that is::

    cp concept_library.md "concept_library.md.bak-$(date -u '+%Y%m%dT%H%M%SZ')"

The ``$(date ...)`` makes the destination path something only knowable at
execution time, so the permission layer cannot validate it up front and
asks a human to approve. In an unattended scheduled run there is nobody
to approve, the backup fails, and FAILSAFE says abort — so the file is
never written. ``concept_library.md`` sat unchanged from 2026-05-11 to
2026-08-07 for exactly this reason.

The fix is not to special-case that one file (the policy covers seven,
and grows). It is to stop asking an agent to compose a timestamped path
in the shell at all. The agent writes new content to ``<file>.new`` with
its normal Write tool, then runs::

    python3 scripts/safe_write.py --pair concept_library.md concept_library.md.new

That command line is fully static — one ``Bash(python3:*)`` allow rule
covers it, today and for every file added later.

Multi-file writes
-----------------
``/review`` mutates tracker + style guide + concept library in one pass.
FAILSAFE requires all of them backed up *before* any is committed, so a
failure cannot leave the set half-updated. Passing several ``--pair``
arguments gets that guarantee from this script instead of from the
agent remembering to do it in the right order.

Output
------
A JSON report on stdout: which targets were backed up (and to what),
which were committed, and what failed. The agent should quote this
rather than describing from memory what it thinks happened.

Exit codes
----------
0   all pairs committed
1   nothing was committed (validation or backup failed) — targets untouched
2   partial commit (a rename failed after earlier ones succeeded) — read
    the report, this is the case that needs a human
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from _atomic import (
    _iso_stamp,
    atomic_write_json,
    atomic_write_text,
    backup_file,
    configure_utf8_stdout,
    prune_backups,
)


def _emit(report: Dict[str, Any], code: int) -> int:
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


def _validate(pairs: List[Tuple[Path, Path]]) -> List[str]:
    """Check every pair before touching anything. Returns error strings."""
    errors: List[str] = []
    for target, source in pairs:
        if not source.exists():
            errors.append(f"source missing: {source}")
            continue
        if source.is_dir():
            errors.append(f"source is a directory: {source}")
            continue
        if target.exists() and target.is_dir():
            errors.append(f"target is a directory: {target}")
            continue
        if target.suffix == ".json":
            try:
                json.loads(source.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                # A tracker that does not parse must never reach disk —
                # this is the failure mode the whole policy exists for.
                errors.append(f"source is not valid JSON: {source} ({exc})")
    return errors


def main(argv: List[str] | None = None) -> int:
    configure_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="Back up and atomically commit prepared files (FAILSAFE).",
    )
    parser.add_argument(
        "--pair",
        nargs=2,
        action="append",
        metavar=("TARGET", "SOURCE"),
        required=True,
        help="Destination file and the prepared file to move into it. "
             "Repeat for a multi-file write; all targets are backed up "
             "before any is committed.",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=5,
        help="Backups to retain per target (default 5, per FAILSAFE).",
    )
    parser.add_argument(
        "--keep-source",
        action="store_true",
        help="Leave the prepared source file on disk after committing. "
             "By default it is removed, since it is a staging artifact.",
    )
    args = parser.parse_args(argv)

    pairs = [(Path(t), Path(s)) for t, s in args.pair]
    stamp = _iso_stamp()
    report: Dict[str, Any] = {
        "stamp": stamp,
        "keep": args.keep,
        "pairs": [{"target": str(t), "source": str(s)} for t, s in pairs],
        "backed_up": [],
        "committed": [],
        "errors": [],
    }

    errors = _validate(pairs)
    if errors:
        report["errors"] = errors
        report["result"] = "aborted-before-backup"
        return _emit(report, 1)

    # Phase 1 — back up every target first. Abort the whole set on the
    # first failure; nothing has been committed yet, so the user's files
    # are all still intact.
    for target, _ in pairs:
        try:
            bak = backup_file(target, stamp=stamp)
        except OSError as exc:
            report["errors"].append(f"backup failed for {target}: {exc}")
            report["result"] = "aborted-during-backup"
            return _emit(report, 1)
        report["backed_up"].append(
            {"target": str(target), "backup": str(bak) if bak else None,
             "note": None if bak else "new file, nothing to back up"}
        )

    # Phase 2 — commit. Backups already exist, so pass backup=False and
    # prune once at the end.
    for target, source in pairs:
        try:
            text = source.read_text(encoding="utf-8")
            if target.suffix == ".json":
                atomic_write_json(target, json.loads(text), backup=False)
            else:
                atomic_write_text(target, text, backup=False)
        except (OSError, ValueError, RuntimeError) as exc:
            report["errors"].append(f"commit failed for {target}: {exc}")
            report["result"] = (
                "partial-commit" if report["committed"] else "aborted-during-commit"
            )
            return _emit(report, 2 if report["committed"] else 1)

        report["committed"].append(str(target))
        prune_backups(target, keep=args.keep)

        if not args.keep_source:
            try:
                source.unlink()
            except OSError:
                # Staging file left behind is cosmetic; the commit stood.
                pass

    report["result"] = "ok"
    return _emit(report, 0)


if __name__ == "__main__":
    sys.exit(main())
