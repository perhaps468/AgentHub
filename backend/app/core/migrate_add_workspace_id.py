# -*- coding: utf-8 -*-
"""One-time migration: add workspace_id column to sessions table.

Usage:
    python -m app.core.migrate_add_workspace_id
"""
import os
import re
from pathlib import Path

import pymysql


def _load_env() -> dict[str, str]:
    env_path = Path(__file__).parent.parent.parent / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def _parse_mysql_url(url: str) -> dict[str, str]:
    m = re.match(
        r"mysql\+pymysql://(?P<user>[^:@]+):(?P<password>[^@]+)@(?P<host>[^:/]+):(?P<port>\d+)/(?P<db>.+)",
        url,
    )
    if not m:
        raise ValueError(f"Cannot parse MySQL URL: {url}")
    creds = m.groupdict()
    # Strip any query string from the database name (e.g. ?charset=utf8mb4)
    creds["db"] = creds["db"].split("?")[0]
    return creds


def _column_exists(conn: pymysql.Connection, table: str, column: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
            (table, column),
        )
        return cur.fetchone()[0] > 0


def _run() -> None:
    env = _load_env()
    raw_url = env.get("DATABASE_URL", "")
    if not raw_url:
        raise RuntimeError("DATABASE_URL not found in backend/.env")

    creds = _parse_mysql_url(raw_url)

    conn = pymysql.connect(
        host=creds["host"],
        port=int(creds["port"]),
        user=creds["user"],
        password=creds["password"],
        database=creds["db"],
        charset="utf8mb4",
    )

    table = "sessions"
    column = "workspace_id"

    try:
        with conn.cursor() as cur:
            if _column_exists(conn, table, column):
                print(f"[OK] Column '{column}' already exists in '{table}', nothing to do.")
                return

            # Add column as nullable (existing rows get NULL = no workspace bound)
            cur.execute(
                f"ALTER TABLE `{table}` "
                f"ADD COLUMN `{column}` VARCHAR(36) NULL AFTER `owner_id`, "
                f"ADD INDEX `ix_sessions_{column}` (`{column}`)"
            )
            conn.commit()
            print(f"[OK] Added column '{column}' to '{table}' with index.")
            print(f"     Existing rows will have NULL (no workspace bound).")
    finally:
        conn.close()


if __name__ == "__main__":
    _run()
