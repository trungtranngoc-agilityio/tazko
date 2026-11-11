"""License check for the Python packages the API ships with.

Walks the runtime requirements of the installed `tazko` package (not the dev
group) and fails on any license outside the allow-list. Run it from the server
environment:  uv run --project backend python tools/check-backend-licenses.py

Allowed: MIT, Apache-2.0, BSD-2/3-Clause, ISC; accepted exceptions Unicode-3.0,
Zlib (D12) and PSF-2.0 (D14).
"""

from __future__ import annotations

import re
import sys
from importlib.metadata import PackageNotFoundError, distribution

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

ALLOWED = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Unicode-3.0",
    "Zlib",
    "PSF-2.0",
}
# Trove classifiers and free-text License fields, for packages without License-Expression.
CLASSIFIERS = {
    "MIT License": "MIT",
    "Apache Software License": "Apache-2.0",
    "BSD License": "BSD-3-Clause",
    "ISC License (ISCL)": "ISC",
    "Python Software Foundation License": "PSF-2.0",
}


def license_ids(dist) -> set[str]:
    meta = dist.metadata
    expression = meta.get("License-Expression")
    if expression:
        # "A OR B" passes when one side is allowed; "A AND B" needs both.
        if " OR " in expression:
            options = [part.strip(" ()") for part in expression.split(" OR ")]
            return {next((o for o in options if o in ALLOWED), options[0])}
        return {part.strip(" ()") for part in re.split(r" AND ", expression)}
    found = {
        CLASSIFIERS.get(c.split(" :: ")[-1], c.split(" :: ")[-1])
        for c in meta.get_all("Classifier") or []
        if c.startswith("License :: OSI Approved ::")
    }
    if not found and meta.get("License") in ALLOWED:
        found = {meta["License"]}
    return found or {"UNKNOWN"}


def main() -> int:
    env = default_environment() | {"extra": ""}
    seen: dict[str, set[str]] = {}
    queue = ["tazko"]
    while queue:
        name = canonicalize_name(queue.pop())
        if name in seen:
            continue
        try:
            dist = distribution(name)
        except PackageNotFoundError:
            print(f"missing package {name}; run uv sync --project backend", file=sys.stderr)
            return 1
        seen[name] = license_ids(dist) if name != "tazko" else {"own"}
        for raw in dist.requires or []:
            req = Requirement(raw)
            if req.marker is None or req.marker.evaluate(env):
                queue.append(req.name)

    bad = {name: ids for name, ids in seen.items() if not ids <= ALLOWED | {"own"}}
    for name, ids in sorted(bad.items()):
        print(f"not allowed: {name} ({', '.join(sorted(ids))})", file=sys.stderr)
    if bad:
        return 1
    print(f"backend licenses ok: {len(seen) - 1} shipped packages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
