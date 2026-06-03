# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


def get_audit_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "backend" / ".audit"


def get_llm_audit_log_path() -> str:
    return str(get_audit_dir() / "llm_traces.jsonl")


def get_group_chat_audit_log_path() -> str:
    return str(get_audit_dir() / "group_chat_traces.jsonl")
