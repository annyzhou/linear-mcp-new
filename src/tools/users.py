# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""User tools.

Tools:
  linear_whoami      -- get the authenticated user's profile (viewer)
  linear_list_users  -- list workspace members
"""

from __future__ import annotations

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from linear.request import _opt_str, _str, graphql
from linear.types import JSONObject, LinearResult, UserInfo


# --- Helpers ---


def _parse_user(raw: JSONObject) -> UserInfo:
    """Parse a raw GraphQL user node into a UserInfo.

    Args:
        raw: Untyped user node from a GraphQL response.

    Returns:
        Parsed UserInfo with coerced fields.

    """
    result = UserInfo(
        id=_str(raw.get("id")),
        name=_str(raw.get("name")),
        email=_opt_str(raw.get("email")),
    )
    return result


# --- Tools ---


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_whoami() -> UserInfo | str:
    """Fetch the authenticated user's profile.

    Returns:
        UserInfo for the current viewer, or an error string on failure.

    """
    query = """
    query Viewer {
        viewer { id name email }
    }
    """
    response: LinearResult = await graphql(query)
    if not response.success:
        return response.error or "Failed to fetch viewer"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    viewer = data.get("viewer")
    if not isinstance(viewer, dict):
        return "Viewer not found"
    result = _parse_user(viewer)
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_list_users(
    first: int = 50,
    after: str | None = None,
    *,
    include_archived: bool = False,
) -> list[UserInfo] | str:
    """List workspace members.

    Args:
        first: Maximum number of users to return.
        after: Cursor for pagination (from a previous response).
        include_archived: Include deactivated users in results.

    Returns:
        List of UserInfo objects, or an error string on failure.

    """
    query = """
    query Users($first: Int, $after: String, $includeArchived: Boolean) {
        users(first: $first, after: $after, includeArchived: $includeArchived) {
            nodes { id name email }
            pageInfo { hasNextPage endCursor }
        }
    }
    """
    variables = {"first": first, "after": after, "includeArchived": include_archived}
    response: LinearResult = await graphql(query, variables)
    if not response.success:
        return response.error or "Failed to list users"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    users_data = data.get("users")
    if not isinstance(users_data, dict):
        return "No users data"
    nodes = users_data.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    result = [_parse_user(node) for node in nodes if isinstance(node, dict)]
    return result


user_tools = [
    linear_whoami,
    linear_list_users,
]
