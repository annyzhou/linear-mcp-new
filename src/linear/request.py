# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Linear GraphQL request dispatch and response helpers.

Linear uses a single GraphQL endpoint (POST /graphql) for all operations.
Unlike REST APIs, every request goes to the same URL with a query body.

Functions:
  graphql(query, variables)  -- dispatch GraphQL query via Dedalus enclave

Coercion helpers (safe extraction from untyped API dicts):
  _str(val, default)         -- coerce to str
  _int(val, default)         -- coerce to int
  _float(val, default)       -- coerce to float
  _opt_str(val)              -- coerce to str | None
  _bool(val, *, default)     -- coerce to bool
  _nested_str(obj, key)      -- extract str from nested dict
"""

from __future__ import annotations

from typing import Any

from dedalus_mcp import HttpMethod, HttpRequest, get_context

from linear.config import linear
from linear.types import LinearResult


# --- GraphQL dispatch ---


async def graphql(
    query: str,
    variables: dict[str, Any] | None = None,
    *,
    signed_url_ttl: int | None = None,
) -> LinearResult:
    """Execute a Linear GraphQL query via the Dedalus enclave.

    All Linear API interaction goes through this single function.
    GraphQL errors (200 with ``errors`` array) are surfaced as
    ``LinearResult(success=False)``.

    Args:
        query: GraphQL query or mutation string.
        variables: GraphQL variables. Optional.
        signed_url_ttl: When set, adds the ``public-file-urls-expire-in``
            header so file-storage URLs in the response carry a temporary
            signature valid for this many seconds.

    Returns:
        LinearResult wrapping the response data or error.

    """
    body: dict[str, Any] = {"query": query}
    if variables:
        body["variables"] = variables

    headers: dict[str, str] | None = None
    if signed_url_ttl is not None:
        headers = {"public-file-urls-expire-in": str(signed_url_ttl)}

    ctx = get_context()
    req = HttpRequest(method=HttpMethod.POST, path="/graphql", body=body)
    if headers is not None:
        req = HttpRequest(
            method=HttpMethod.POST, path="/graphql", body=body, headers=headers
        )
    resp = await ctx.dispatch(linear, req)
    if resp.success and resp.response is not None:
        resp_body = resp.response.body
        if isinstance(resp_body, dict):
            errors = resp_body.get("errors")
            if errors and isinstance(errors, list):
                msg = (
                    errors[0].get("message", "GraphQL error")
                    if isinstance(errors[0], dict)
                    else "GraphQL error"
                )
                result = LinearResult(success=False, error=str(msg))
                return result
            result = LinearResult(success=True, data=resp_body.get("data"))
            return result
        result = LinearResult(success=True, data=resp_body)
        return result

    error = resp.error.message if resp.error else "Request failed"
    result = LinearResult(success=False, error=error)
    return result


# --- Coercion helpers (safe extraction from untyped API dicts) ---


def _str(val: Any, default: str = "") -> str:  # noqa: ANN401 — raw JSON extraction
    """Safely coerce to string."""
    return str(val) if val is not None else default


def _int(val: Any, default: int = 0) -> int:  # noqa: ANN401 — raw JSON extraction
    """Safely coerce to int."""
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _float(val: Any, default: float = 0.0) -> float:  # noqa: ANN401 — raw JSON extraction
    """Safely coerce to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _opt_str(val: Any) -> str | None:  # noqa: ANN401 — raw JSON extraction
    """Safely coerce to optional string."""
    return str(val) if val is not None else None


def _bool(val: Any, *, default: bool = False) -> bool:  # noqa: ANN401 — raw JSON extraction
    """Safely coerce to bool."""
    return bool(val) if val is not None else default


def _nested_str(obj: Any, key: str) -> str | None:  # noqa: ANN401 — raw JSON extraction
    """Extract a string from a nested dict, e.g. ``d.get("user", {}).get("login")``."""
    if isinstance(obj, dict):
        return _opt_str(obj.get(key))
    return None
