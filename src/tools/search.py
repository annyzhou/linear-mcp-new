# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Search tools.

Tools:
  linear_search_issues -- full-text search across issues
"""

from __future__ import annotations

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from linear.request import _int, _nested_str, _opt_str, _str, graphql
from linear.types import IssueInfo, JSONObject, LinearResult


# --- Helpers ---


def _parse_search_issue(raw: JSONObject) -> IssueInfo:
    """Parse a search result node into an IssueInfo.

    Args:
        raw: Untyped issue node from an ``issueSearch`` response.

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
async def linear_search_issues(
    query: str,
    first: int = 25,
    after: str | None = None,
    include_archived: bool = False,
) -> list[IssueInfo] | str:
    """Search issues using full-text natural language queries.

    Uses Linear's ``issueSearch`` endpoint which supports free-form text.

    Args:
        query: Search query string (natural language supported).
        first: Maximum number of results to return.
        after: Cursor for pagination (from a previous response).
        include_archived: Include archived issues in results.

    Returns:
        List of matching IssueInfo objects, or an error string on failure.

    """
    gql = """
    query SearchIssues(
        $query: String!,
        $first: Int,
        $after: String,
        $includeArchived: Boolean
    ) {
        issueSearch(
            query: $query,
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
    """
    variables = {
        "query": query,
        "first": first,
        "after": after,
        "includeArchived": include_archived,
    }
    response: LinearResult = await graphql(gql, variables)
    if not response.success:
        return response.error or "Failed to search issues"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    search_data = data.get("issueSearch")
    if not isinstance(search_data, dict):
        return "No search results"
    nodes = search_data.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    result = [_parse_search_issue(node) for node in nodes if isinstance(node, dict)]
    return result


search_tools = [
    linear_search_issues,
]
