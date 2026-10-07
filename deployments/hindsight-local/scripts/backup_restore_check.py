#!/usr/bin/env python3
"""Logical backup/restore rehearsal for this synthetic local deployment only."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import asyncpg

ROOT = Path(__file__).resolve().parents[1]
BINDIR = Path.home() / ".pg0/installation/18.1.0/bin"
RESTORE_DB = "contextdb_research_restore"
TABLES = ["banks", "documents", "chunks", "memory_units", "entities", "memory_links"]


async def connect(port, database="hindsight"):
    return await asyncpg.connect(host="127.0.0.1", port=port, user="hindsight",
                                 password="hindsight", database=database)


async def fingerprint(conn):
    result = {}
    for table in TABLES:
        rows = await conn.fetch(f"SELECT row_to_json(t)::text AS body FROM public.{table} t")
        canonical = "\n".join(sorted(json.dumps(json.loads(r["body"]), sort_keys=True, ensure_ascii=False) for r in rows))
        result[table] = {"rows": len(rows), "sha256": hashlib.sha256(canonical.encode()).hexdigest()}
    return result


async def main():
    backup_dir = ROOT / ".runtime/backups"
    backup_dir.mkdir(exist_ok=True)
    path = backup_dir / "hindsight-local.dump"
    env = os.environ.copy()
    env["PGPASSWORD"] = "hindsight"  # Task-specific disposable local PG only.
    source = await connect(55432)
    before = await fingerprint(source)
    pending = await source.fetchval("SELECT count(*) FROM public.async_operations WHERE status IN ('pending','processing')")
    if pending:
        raise RuntimeError("Wait for synthetic background operations before comparing a stable snapshot")
    with (ROOT / "evidence/backup-restore-command.log").open("w") as log:
        subprocess.run([str(BINDIR / "pg_dump"), "-h", "127.0.0.1", "-p", "55432", "-U", "hindsight",
                        "-d", "hindsight", "-Fc", "-f", str(path)], env=env, check=True, stdout=log, stderr=log)
        admin = await connect(55433)
        if await admin.fetchval("SELECT 1 FROM pg_database WHERE datname=$1", RESTORE_DB):
            raise RuntimeError("Restore target exists; refusing to overwrite")
        await admin.execute(f"CREATE DATABASE {RESTORE_DB}")
        await admin.close()
        subprocess.run([str(BINDIR / "pg_restore"), "--exit-on-error", "-h", "127.0.0.1", "-p", "55433",
                        "-U", "hindsight", "-d", RESTORE_DB, str(path)], env=env, check=True, stdout=log, stderr=log)
    target = await connect(55433, RESTORE_DB)
    after = await fingerprint(target)
    result = {"method": "pg_dump custom format -> pg_restore into a new database on a second local PG",
              "source_port": 55432, "target_port": 55433, "target_database": RESTORE_DB,
              "backup_bytes": path.stat().st_size, "backup_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "before": before, "after": after, "equal": before == after,
              "limitations": "Logical snapshot of synthetic data, not PITR, failover, RDS HA or online migration"}
    (ROOT / "evidence/backup-restore-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    await source.close()
    await target.close()
    assert result["equal"], "Snapshot content differs"
    print("PASS: six core tables have identical row counts and content hashes after restore")


if __name__ == "__main__":
    asyncio.run(main())
