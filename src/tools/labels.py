# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Label tools.

Tools:
  linear_list_labels   -- list labels for the workspace or team
  linear_create_label  -- create a new label
"""

from __future__ import annotations

from typing import Any

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from linear.request import _opt_str, _str, graphql
from linear.types import JSONObject, LabelInfo, LinearResult


# --- Helpers ---


def _parse_label(raw: JSONObject) -> LabelInfo:
    """Parse a raw GraphQL label node into a LabelInfo.

    Args:
        raw: Untyped label node from a GraphQL response.

    Returns:
        Parsed LabelInfo with coerced fields.

    """
    result = LabelInfo(
        id=_str(raw.get("id")),
        name=_str(raw.get("name")),
        color=_opt_str(raw.get("color")),
    )
    return result


# --- Tools ---


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_list_labels(
    team_id: str | None = None,
    first: int = 50,
    after: str | None = None,
) -> list[LabelInfo] | str:
    """List labels for the workspace, optionally scoped to a team.

    When ``team_id`` is provided, only that team's labels are returned.
    Otherwise, all workspace-level labels are returned.

    Args:
        team_id: Team UUID to scope results. Optional.
        first: Maximum number of labels to return.
        after: Cursor for pagination (from a previous response).

    Returns:
        List of LabelInfo objects, or an error string on failure.

    """
    if team_id:
        query = """
        query TeamLabels($id: String!, $first: Int, $after: String) {
            team(id: $id) {
                labels(first: $first, after: $after) {
                    nodes { id name color }
                    pageInfo { hasNextPage endCursor }
                }
            }
        }
        """
        variables: dict[str, Any] = {"id": team_id, "first": first, "after": after}
        response: LinearResult = await graphql(query, variables)
        if not response.success:
            return response.error or "Failed to list labels"
        data = response.data
        if not isinstance(data, dict):
            return "Unexpected response"
        team_data = data.get("team")
        if not isinstance(team_data, dict):
            return "Team not found"
        labels_data = team_data.get("labels")
    else:
        query = """
        query Labels($first: Int, $after: String) {
            issueLabels(first: $first, after: $after) {
                nodes { id name color }
                pageInfo { hasNextPage endCursor }
            }
        }
        """
        variables = {"first": first, "after": after}
        response = await graphql(query, variables)
        if not response.success:
            return response.error or "Failed to list labels"
        data = response.data
        if not isinstance(data, dict):
            return "Unexpected response"
        labels_data = data.get("issueLabels")

    if not isinstance(labels_data, dict):
        return "No labels data"
    nodes = labels_data.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    result = [_parse_label(node) for node in nodes if isinstance(node, dict)]
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=False))
async def linear_create_label(
    name: str,
    team_id: str | None = None,
    color: str | None = None,
) -> LabelInfo | str:
    """Create a new label.

    If ``team_id`` is omitted, the label is created at workspace scope.

    Args:
        name: Label name.
        team_id: Team UUID to scope the label to. Optional.
        color: Hex color string (e.g. ``#ff0000``). Optional.

    Returns:
        Created LabelInfo, or an error string on failure.

    """
    query = """
    mutation LabelCreate($input: IssueLabelCreateInput!) {
        issueLabelCreate(input: $input) {
            success
            issueLabel { id name color }
        }
    }
    """
    input_data: dict[str, Any] = {"name": name}
    if team_id is not None:
        input_data["teamId"] = team_id
    if color is not None:
        input_data["color"] = color

    response: LinearResult = await graphql(query, {"input": input_data})
    if not response.success:
        return response.error or "Failed to create label"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    payload = data.get("issueLabelCreate")
    if not isinstance(payload, dict) or not payload.get("success"):
        return "Label creation failed"
    label_data = payload.get("issueLabel")
    if not isinstance(label_data, dict):
        return "No label in response"
    result = _parse_label(label_data)
    return result


label_tools = [
    linear_list_labels,
    linear_create_label,
]
