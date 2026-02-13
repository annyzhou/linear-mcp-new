# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Issue tools.

Tools:
  linear_get_issue     -- get issue by ID or identifier (e.g. ENG-123)
  linear_list_issues   -- list issues with optional filter passthrough
  linear_create_issue  -- create a new issue
  linear_update_issue  -- update an existing issue
"""

from __future__ import annotations

from typing import Any

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from linear.request import _int, _nested_str, _opt_str, _str, graphql
from linear.types import IssueInfo, JSONObject, LinearResult


# --- Fragments ---

_ISSUE_FIELDS = """
    id identifier title priority createdAt updatedAt
    state { name }
    assignee { name }
    labels { nodes { name } }
"""


# --- Helpers ---


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


# --- Tools ---


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_get_issue(issue_id: str) -> IssueInfo | str:
    """Fetch a Linear issue by ID or identifier.

    Accepts a UUID or human-readable identifier like ``ENG-123``.
    Returns the full issue including description.

    Args:
        issue_id: UUID or human-readable identifier (e.g. ``ENG-123``).

    Returns:
        IssueInfo with full detail, or an error string on failure.

    """
    query = f"""
    query GetIssue($id: String!) {{
        issue(id: $id) {{ {_ISSUE_FIELDS} description }}
    }}
    """
    response: LinearResult = await graphql(query, {"id": issue_id})
    if not response.success:
        return response.error or "Failed to fetch issue"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    issue_data = data.get("issue")
    if not isinstance(issue_data, dict):
        return "Issue not found"
    result = _parse_issue(issue_data)
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_list_issues(
    filter: JSONObject | None = None,
    first: int = 50,
    after: str | None = None,
    order_by: str = "createdAt",
    include_archived: bool = False,
) -> list[IssueInfo] | str:
    """List issues with optional GraphQL filter passthrough.

    The ``filter`` param accepts a Linear IssueFilter dict, e.g.
    ``{"assignee": {"email": {"eq": "me@co.com"}}, "priority": {"lte": 2}}``.
    See https://linear.app/developers/filtering for the full schema.

    Args:
        filter: Raw GraphQL IssueFilter dictionary. Passed through as-is.
        first: Maximum number of issues to return.
        after: Cursor for pagination (from a previous response).
        order_by: Sort field — ``createdAt`` or ``updatedAt``.
        include_archived: Include archived issues in results.

    Returns:
        List of IssueInfo objects, or an error string on failure.

    """
    query = f"""
    query Issues(
        $filter: IssueFilter,
        $first: Int,
        $after: String,
        $orderBy: PaginationOrderBy,
        $includeArchived: Boolean
    ) {{
        issues(
            filter: $filter,
            first: $first,
            after: $after,
            orderBy: $orderBy,
            includeArchived: $includeArchived
        ) {{
            nodes {{ {_ISSUE_FIELDS} }}
            pageInfo {{ hasNextPage endCursor }}
        }}
    }}
    """
    variables: dict[str, Any] = {
        "filter": filter,
        "first": first,
        "after": after,
        "orderBy": order_by,
        "includeArchived": include_archived,
    }
    response: LinearResult = await graphql(query, variables)
    if not response.success:
        return response.error or "Failed to list issues"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    issues_data = data.get("issues")
    if not isinstance(issues_data, dict):
        return "No issues data"
    nodes = issues_data.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    result = [_parse_issue(node) for node in nodes if isinstance(node, dict)]
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=False))
async def linear_create_issue(
    team_id: str,
    title: str,
    description: str | None = None,
    assignee_id: str | None = None,
    state_id: str | None = None,
    priority: int | None = None,
    label_ids: list[str] | None = None,
    cycle_id: str | None = None,
    project_id: str | None = None,
    estimate: int | None = None,
    create_as_user: str | None = None,
    display_icon_url: str | None = None,
) -> IssueInfo | str:
    """Create a new issue.

    If ``state_id`` is omitted, Linear defaults to the team's first
    Backlog state (or Triage if enabled).

    When the OAuth token uses ``actor=app``, mutations come from the app.
    Set ``create_as_user`` and ``display_icon_url`` to attribute the action
    to a human name and avatar rendered as *User (via Application)*.

    Args:
        team_id: Team UUID that owns the issue.
        title: Issue title.
        description: Markdown body. Optional.
        assignee_id: User UUID to assign. Optional.
        state_id: Workflow state UUID. Optional.
        priority: Priority level (0=none, 1=urgent, 2=high, 3=medium, 4=low).
        label_ids: Label UUIDs to attach. Optional.
        cycle_id: Cycle UUID to assign to. Optional.
        project_id: Project UUID to assign to. Optional.
        estimate: Point estimate. Optional.
        create_as_user: Display name for the acting user (``actor=app`` only).
        display_icon_url: Avatar URL for the acting user (``actor=app`` only).

    Returns:
        Created IssueInfo, or an error string on failure.

    """
    query = f"""
    mutation IssueCreate($input: IssueCreateInput!) {{
        issueCreate(input: $input) {{
            success
            issue {{ {_ISSUE_FIELDS} }}
        }}
    }}
    """
    input_data: dict[str, Any] = {"teamId": team_id, "title": title}
    if description is not None:
        input_data["description"] = description
    if assignee_id is not None:
        input_data["assigneeId"] = assignee_id
    if state_id is not None:
        input_data["stateId"] = state_id
    if priority is not None:
        input_data["priority"] = priority
    if label_ids is not None:
        input_data["labelIds"] = label_ids
    if cycle_id is not None:
        input_data["cycleId"] = cycle_id
    if project_id is not None:
        input_data["projectId"] = project_id
    if estimate is not None:
        input_data["estimate"] = estimate
    if create_as_user is not None:
        input_data["createAsUser"] = create_as_user
    if display_icon_url is not None:
        input_data["displayIconUrl"] = display_icon_url

    response: LinearResult = await graphql(query, {"input": input_data})
    if not response.success:
        return response.error or "Failed to create issue"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    payload = data.get("issueCreate")
    if not isinstance(payload, dict) or not payload.get("success"):
        return "Issue creation failed"
    issue_data = payload.get("issue")
    if not isinstance(issue_data, dict):
        return "No issue in response"
    result = _parse_issue(issue_data)
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=False))
async def linear_update_issue(
    issue_id: str,
    title: str | None = None,
    description: str | None = None,
    state_id: str | None = None,
    assignee_id: str | None = None,
    priority: int | None = None,
    label_ids: list[str] | None = None,
    cycle_id: str | None = None,
    project_id: str | None = None,
    estimate: int | None = None,
) -> IssueInfo | str:
    """Update an existing issue.

    Only provided fields are modified; omitted fields are left unchanged.

    Args:
        issue_id: UUID or human-readable identifier (e.g. ``ENG-123``).
        title: New title. Optional.
        description: New markdown body. Optional.
        state_id: New workflow state UUID. Optional.
        assignee_id: New assignee UUID. Optional.
        priority: New priority (0=none, 1=urgent, 2=high, 3=medium, 4=low).
        label_ids: Replacement label UUIDs (replaces all). Optional.
        cycle_id: New cycle UUID. Optional.
        project_id: New project UUID. Optional.
        estimate: New point estimate. Optional.

    Returns:
        Updated IssueInfo, or an error string on failure.

    """
    query = f"""
    mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {{
        issueUpdate(id: $id, input: $input) {{
            success
            issue {{ {_ISSUE_FIELDS} }}
        }}
    }}
    """
    input_data: dict[str, Any] = {}
    if title is not None:
        input_data["title"] = title
    if description is not None:
        input_data["description"] = description
    if state_id is not None:
        input_data["stateId"] = state_id
    if assignee_id is not None:
        input_data["assigneeId"] = assignee_id
    if priority is not None:
        input_data["priority"] = priority
    if label_ids is not None:
        input_data["labelIds"] = label_ids
    if cycle_id is not None:
        input_data["cycleId"] = cycle_id
    if project_id is not None:
        input_data["projectId"] = project_id
    if estimate is not None:
        input_data["estimate"] = estimate

    if not input_data:
        return "No fields to update"

    response: LinearResult = await graphql(query, {"id": issue_id, "input": input_data})
    if not response.success:
        return response.error or "Failed to update issue"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    payload = data.get("issueUpdate")
    if not isinstance(payload, dict) or not payload.get("success"):
        return "Issue update failed"
    issue_data = payload.get("issue")
    if not isinstance(issue_data, dict):
        return "No issue in response"
    result = _parse_issue(issue_data)
    return result


issue_tools = [
    linear_get_issue,
    linear_list_issues,
    linear_create_issue,
    linear_update_issue,
]
