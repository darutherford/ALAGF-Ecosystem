"""Shared test fixtures.

Governance rationale: tests must run in a clean ledger state. Cross-test
contamination would compromise reconstructability assertions. Each test
starts with empty registry and hash chain directories.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest


_MULTIAGENT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _clean_ledger() -> None:
    """Wipe the ledger and registry before each test."""
    ledger_root = _MULTIAGENT_ROOT / "ledger"
    for sub in ("agent_registry", "hash_chain/sessions"):
        target = ledger_root / sub
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
    yield


@pytest.fixture
def session_id() -> str:
    return "SESSION_abcdef01"


@pytest.fixture
def auditor_id() -> str:
    return "AUDITOR_DALE_001"
