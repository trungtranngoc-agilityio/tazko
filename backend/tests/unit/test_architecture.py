"""Rules the code layout must keep. Each test names the rule it guards."""

from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "tazko"

# Only these files may reach a company's database without the membership check.
TENANT_ACCESS = {"db/tenant.py", "modules/orgs/service.py", "main.py"}


def test_company_files_are_reached_only_through_open_company() -> None:
    """CLAUDE.md: a handler can never touch a company the caller is not in.
    Everything else goes through tazko.modules.orgs.service.open_company."""
    pattern = re.compile(r"\btenants\.(get|create)\(|\bTenantsDep\b|app\.state\.tenants")
    offenders = [
        str(path.relative_to(SRC)).replace("\\", "/")
        for path in SRC.rglob("*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
        and str(path.relative_to(SRC)).replace("\\", "/") not in TENANT_ACCESS
    ]
    assert offenders == []
