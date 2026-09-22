# FAILSAFE — Persistent-State Write Policy

threads-bench only writes under `benchmarks/`. This is the write policy for those files.

Version: 1.0.0 (trimmed from AK-Threads-Booster FAILSAFE)

---

## Files under this policy

Destructive writes — require backup + atomic replace:

- `benchmarks/opportunities.md`
- `benchmarks/playbook.md`

Append-only logs — require atomic append, no backup needed:

- `benchmarks/bench.log`
- `benchmarks/index.jsonl`（每則對標貼文一行，累積不覆寫。別人的貼文刪掉就永遠沒了，所以第一次抓到就要連原文摘要一起寫進來）

Reports — write-once, new file per run:

- `benchmarks/reports/<date>-<topic_id>.md`

---

## Policy — destructive writes

**Do not compose the backup command yourself. Call `scripts/safe_write.py`.**

1. Write the new content to `<filename>.new` with the `Write` tool.
2. Commit it:

```bash
python3 <skill-root>/scripts/safe_write.py --pair benchmarks/opportunities.md benchmarks/opportunities.md.new
```

Several files in one pass — repeat `--pair`:

```bash
python3 <skill-root>/scripts/safe_write.py \
  --pair benchmarks/opportunities.md benchmarks/opportunities.md.new \
  --pair benchmarks/playbook.md benchmarks/playbook.md.new
```

The script backs up **every** target before committing **any** of them, writes atomically,
prunes to the 5 most recent `.bak-*` per file, and prints a JSON report naming each backup
it made. Quote that report; do not describe the outcome from memory. Exit codes: `0` all
committed, `1` nothing committed (targets untouched), `2` partial commit, which needs a human.

### Why a script and not `cp`

The obvious spelling is:

```bash
cp opportunities.md "opportunities.md.bak-$(date -u '+%Y%m%dT%H%M%SZ')"
```

`$(date ...)` makes the destination knowable only at execution time, so the permission
layer cannot validate it in advance and asks a human to approve. Unattended runs have no
human, the backup fails, and the file is silently never written. A static command line
(`Bash(python3:*)`) has no such hole.

### Manual fallback

Only when `scripts/safe_write.py` is genuinely missing:

1. **Backup.** Copy the current file to `<filename>.bak-<ISO>`, compact UTC (`20260422T143012Z`).
   If the copy fails, **abort** and say which file failed and why.
2. **Write to temp.** Write new content to `<filename>.tmp-<ISO>`.
3. **Atomic rename.** Rename `.tmp-<ISO>` over `<filename>`. This is the commit point.
4. **Prune.** Keep at most the **5 most recent** `.bak-*` per filename.

---

## Policy — append-only logs

1. Read-modify-write is **not** allowed for logs. Always open in append mode and write one JSON line (newline-terminated).
2. Do not rewrite old entries. If an entry is later discovered to be wrong, write a new entry that supersedes it (include the prior `run_id` in a `supersedes` field).
3. No backup needed. The append-only nature is the safety mechanism.

---

## Recovery

If a user reports a corrupted file:

1. Ask which file and when the corruption was first noticed.
2. List the available `.bak-*` copies in that directory.
3. Let the user pick which backup to restore. Do not auto-pick.
4. Before overwriting, back up the **current (corrupted)** file as `<filename>.bak-<ISO>-corrupted`.
