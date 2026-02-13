# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Comment tools.

Tools:
  linear_list_comments   -- list comments on an issue
  linear_create_comment  -- add a comment to an issue
"""

from __future__ import annotations

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from linear.request import _nested_str, _opt_str, _str, graphql
from linear.types import CommentInfo, JSONObject, LinearResult


# --- Helpers ---


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


# --- Tools ---


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_list_comments(
    issue_id: str,
    first: int = 50,
    after: str | None = None,
) -> list[CommentInfo] | str:
    """List comments on an issue.

    Args:
        issue_id: UUID or identifier of the parent issue.
        first: Maximum number of comments to return.
        after: Cursor for pagination (from a previous response).

    Returns:
        List of CommentInfo objects, or an error string on failure.

    """
    query = """
    query IssueComments($id: String!, $first: Int, $after: String) {
        issue(id: $id) {
            comments(first: $first, after: $after) {
                nodes {
                    id body createdAt
                    user { name }
                }
                pageInfo { hasNextPage endCursor }
            }
        }
    }
    """
    variables = {"id": issue_id, "first": first, "after": after}
    response: LinearResult = await graphql(query, variables)
    if not response.success:
        return response.error or "Failed to list comments"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    issue_data = data.get("issue")
    if not isinstance(issue_data, dict):
        return "Issue not found"
    comments_data = issue_data.get("comments")
    if not isinstance(comments_data, dict):
        return "No comments data"
    nodes = comments_data.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    result = [_parse_comment(node) for node in nodes if isinstance(node, dict)]
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=False))
async def linear_create_comment(
    issue_id: str,
    body: str,
    create_as_user: str | None = None,
    display_icon_url: str | None = None,
) -> CommentInfo | str:
    """Add a comment to an issue.

    The body supports full markdown including mentions via plain Linear
    URLs (e.g. ``https://linear.app/team/issue/ENG-123``).

    When the OAuth token uses ``actor=app``, set ``create_as_user`` and
    ``display_icon_url`` to attribute the comment to a human name and
    avatar rendered as *User (via Application)*.

    Args:
        issue_id: UUID or identifier of the parent issue.
        body: Comment body in markdown.
        create_as_user: Display name for the acting user (``actor=app`` only).
        display_icon_url: Avatar URL for the acting user (``actor=app`` only).

    Returns:
        Created CommentInfo, or an error string on failure.

    """
    query = """
    mutation CommentCreate($input: CommentCreateInput!) {
        commentCreate(input: $input) {
            success
            comment {
                id body createdAt
                user { name }
            }
        }
    }
    """
    input_data: dict[str, str] = {"issueId": issue_id, "body": body}
    if create_as_user is not None:
        input_data["createAsUser"] = create_as_user
    if display_icon_url is not None:
        input_data["displayIconUrl"] = display_icon_url
    response: LinearResult = await graphql(query, {"input": input_data})
    if not response.success:
        return response.error or "Failed to create comment"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    payload = data.get("commentCreate")
    if not isinstance(payload, dict) or not payload.get("success"):
        return "Comment creation failed"
    comment_data = payload.get("comment")
    if not isinstance(comment_data, dict):
        return "No comment in response"
    result = _parse_comment(comment_data)
    return result


comment_tools = [
    linear_list_comments,
    linear_create_comment,
]
