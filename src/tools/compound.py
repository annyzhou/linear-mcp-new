# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Compound tools — common multi-step workflows in a single call.

Tools:
  linear_issue_context  -- full context for an issue (details + comments + states)
  linear_my_issues      -- issues assigned to the authenticated user
"""

from __future__ import annotations

from typing import Any

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from linear.request import _float, _int, _nested_str, _opt_str, _str, graphql
from linear.types import (
    CommentInfo,
    IssueContextInfo,
    IssueInfo,
    JSONObject,
    LinearResult,
    WorkflowStateInfo,
)


# --- Shared parsing (re-used from sibling modules) ---
#
# Rather than importing private helpers across module boundaries, we
# inline the lightweight parsing here.  The cost of a few lines of
# duplication is lower than the cost of coupling tool modules.


def _parse_issue(raw: JSONObject) -> IssueInfo:
    """Parse a raw GraphQL issue node into an IssueInfo.

    Args:
        raw: Untyped issue node from a GraphQL response.

    Returns:
        Parsed IssueInfo with coerced fields.

    """
    state_node = raw.get("state")
    assignee_node = raw.get("assignee")
    label_nodes = raw.get("labels", {})
    labels: list[str] = []
    if isinstance(label_nodes, dict):
        nodes = label_nodes.get("nodes", [])
        if isinstance(nodes, list):
            labels = [
                _str(node.get("name"))
                for node in nodes
                if isinstance(node, dict) and node.get("name")
            ]
    result = IssueInfo(
        id=_str(raw.get("id")),
        identifier=_str(raw.get("identifier")),
        title=_str(raw.get("title")),
        description=_opt_str(raw.get("description")),
        state=_nested_str(state_node, "name"),
        priority=_int(raw.get("priority")),
        assignee=_nested_str(assignee_node, "name"),
        labels=labels,
        created_at=_opt_str(raw.get("createdAt")),
        updated_at=_opt_str(raw.get("updatedAt")),
    )
    return result


def _parse_comment(raw: JSONObject) -> CommentInfo:
    """Parse a raw GraphQL comment node into a CommentInfo.

    Args:
        raw: Untyped comment node from a GraphQL response.

    Returns:
        Parsed CommentInfo with coerced fields.

    """
    result = CommentInfo(
        id=_str(raw.get("id")),
        body=_str(raw.get("body")),
        user=_nested_str(raw.get("user"), "name"),
        created_at=_opt_str(raw.get("createdAt")),
    )
    return result


def _parse_state(raw: JSONObject) -> WorkflowStateInfo:
    """Parse a raw GraphQL workflow state node into a WorkflowStateInfo.

    Args:
        raw: Untyped state node from a GraphQL response.

    Returns:
        Parsed WorkflowStateInfo with coerced fields.

    """
    result = WorkflowStateInfo(
        id=_str(raw.get("id")),
        name=_str(raw.get("name")),
        type=_str(raw.get("type")),
        color=_opt_str(raw.get("color")),
        position=_float(raw.get("position")),
    )
    return result


# --- Tools ---


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_issue_context(issue_id: str) -> IssueContextInfo | str:
    """Fetch full context for an issue in a single round-trip.

    Retrieve the issue itself (with description), its comment thread,
    and the team's workflow states. This is the standard starting point
    when an agent is delegated or mentioned on a Linear issue.

    Accepts UUID or identifier (e.g. ENG-123).

    Args:
        issue_id: UUID or human-readable identifier (e.g. ``ENG-123``).

    Returns:
        IssueContextInfo containing issue details, comments, and valid
        workflow states, or an error string on failure.

    """
    query = """
    query IssueContext($id: String!) {
        issue(id: $id) {
            id identifier title description priority createdAt updatedAt
            state { name }
            assignee { name }
            labels { nodes { name } }
            comments(first: 50) {
                nodes {
                    id body createdAt
                    user { name }
                }
            }
            team {
                states {
                    nodes { id name type color position }
                }
            }
        }
    }
    """
    response: LinearResult = await graphql(query, {"id": issue_id})
    if not response.success:
        return response.error or "Failed to fetch issue context"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    issue_data = data.get("issue")
    if not isinstance(issue_data, dict):
        return "Issue not found"

    # Parse issue.
    issue = _parse_issue(issue_data)

    # Parse comments.
    comments_data = issue_data.get("comments", {})
    comment_nodes = (
        comments_data.get("nodes", []) if isinstance(comments_data, dict) else []
    )
    comments = [_parse_comment(n) for n in comment_nodes if isinstance(n, dict)]

    # Parse team workflow states.
    team_data = issue_data.get("team", {})
    states_data = team_data.get("states", {}) if isinstance(team_data, dict) else {}
    state_nodes = states_data.get("nodes", []) if isinstance(states_data, dict) else []
    states = [_parse_state(n) for n in state_nodes if isinstance(n, dict)]

    result = IssueContextInfo(issue=issue, comments=comments, states=states)
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_my_issues(
    first: int = 50,
    after: str | None = None,
    include_archived: bool = False,
) -> list[IssueInfo] | str:
    """Fetch issues assigned to the authenticated user.

    Shortcut for the ``whoami`` then ``list_issues(filter: assignee)``
    two-step pattern. Uses ``viewer.assignedIssues`` directly.

    Args:
        first: Maximum number of issues to return.
        after: Cursor for pagination (from a previous response).
        include_archived: Include archived issues in results.

    Returns:
        List of assigned IssueInfo objects, or an error string on failure.

    """
    query = """
    query MyIssues($first: Int, $after: String, $includeArchived: Boolean) {
        viewer {
            assignedIssues(
                first: $first,
                after: $after,
                includeArchived: $includeArchived
            ) {
                nodes {
                    id identifier title priority createdAt updatedAt
                    state { name }
                    assignee { name }
                    labels { nodes { name } }
                }
                pageInfo { hasNextPage endCursor }
            }
        }
    }
    """
    variables: dict[str, Any] = {
        "first": first,
        "after": after,
        "includeArchived": include_archived,
    }
    response: LinearResult = await graphql(query, variables)
    if not response.success:
        return response.error or "Failed to fetch assigned issues"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    viewer = data.get("viewer")
    if not isinstance(viewer, dict):
        return "Viewer not found"
    assigned = viewer.get("assignedIssues")
    if not isinstance(assigned, dict):
        return "No assigned issues data"
    nodes = assigned.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    result = [_parse_issue(node) for node in nodes if isinstance(node, dict)]
    return result


compound_tools = [
    linear_issue_context,
    linear_my_issues,
]
