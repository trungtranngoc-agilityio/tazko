"""Field types shared by the API contracts (modules/*/schemas.py)."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Key = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
Background = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Description = Annotated[str, StringConstraints(max_length=2000)]
# A SQLite integer: a bigger id would crash the query instead of answering 404 or 422.
Id = Annotated[int, Field(ge=1, le=2**63 - 1)]
