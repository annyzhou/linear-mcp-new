# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Attachment tools — link external resources to Linear issues.

Tools:
  linear_get_attachment        -- fetch attachment by ID
  linear_get_attachment_by_url -- fetch attachment(s) by URL
  linear_create_attachment     -- create or update attachment (URL is idempotent per-issue)
  linear_update_attachment     -- update an existing attachment by ID
"""

from __future__ import annotations

from typing import Any

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from linear.request import _opt_str, _str, graphql
from linear.types import AttachmentInfo, JSONObject, LinearResult


_ATTACHMENT_FIELDS = "id url title subtitle"


def _parse_attachment(raw: JSONObject) -> AttachmentInfo:
    """Parse a raw GraphQL attachment node into an AttachmentInfo.

    Args:
        raw: Untyped attachment node from a GraphQL response.

    Returns:
        Parsed AttachmentInfo with coerced fields.

    """
    return AttachmentInfo(
        id=_str(raw.get("id")),
        url=_str(raw.get("url")),
        title=_opt_str(raw.get("title")),
        subtitle=_opt_str(raw.get("subtitle")),
    )


# --- Tools ---


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_get_attachment(attachment_id: str) -> AttachmentInfo | str:
    """Fetch a single attachment by ID.

    Args:
        attachment_id: Attachment UUID.

    Returns:
        AttachmentInfo, or an error string on failure.

    """
    query = f"""
    query Attachment($id: String!) {{
        attachment(id: $id) {{ {_ATTACHMENT_FIELDS} }}
    }}
    """
    response: LinearResult = await graphql(query, {"id": attachment_id})
    if not response.success:
        return response.error or "Failed to fetch attachment"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    attachment = data.get("attachment")
    if not isinstance(attachment, dict):
        return "Attachment not found"
    return _parse_attachment(attachment)


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_get_attachment_by_url(url: str) -> list[AttachmentInfo] | str:
    """Fetch attachments by their external URL.

    Linear uses the attachment URL as an idempotent key per-issue, so
    this query returns all attachments sharing the given URL (typically
    one per issue).

    Args:
        url: External URL to look up.

    Returns:
        List of matching AttachmentInfo objects, or an error string on failure.

    """
    query = f"""
    query AttachmentsByURL($url: String!) {{
        attachmentsForURL(url: $url) {{
            nodes {{ {_ATTACHMENT_FIELDS} }}
        }}
    }}
    """
    response: LinearResult = await graphql(query, {"url": url})
    if not response.success:
        return response.error or "Failed to fetch attachments"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    container = data.get("attachmentsForURL")
    if not isinstance(container, dict):
        return "No attachment data"
    nodes = container.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    return [_parse_attachment(n) for n in nodes if isinstance(n, dict)]


@tool(annotations=ToolAnnotations(readOnlyHint=False))
async def linear_create_attachment(
    issue_id: str,
    url: str,
    title: str | None = None,
    subtitle: str | None = None,
    icon_url: str | None = None,
    metadata: dict[str, Any] | None = None,
    create_as_user: str | None = None,
    display_icon_url: str | None = None,
) -> AttachmentInfo | str:
    """Create an attachment on an issue, or update if the URL already exists.

    The ``url`` is idempotent per-issue: calling with the same URL on the
    same issue updates the existing attachment rather than creating a
    duplicate.

    Args:
        issue_id: UUID or identifier of the parent issue.
        url: External URL to link.
        title: Display title. Optional.
        subtitle: Display subtitle (supports ``{var__since}`` date formatting). Optional.
        icon_url: Override icon URL (png or jpg). Optional.
        metadata: Arbitrary key-value metadata dict. Optional.
        create_as_user: Display name for the acting user (``actor=app`` only).
        display_icon_url: Avatar URL for the acting user (``actor=app`` only).

    Returns:
        Created or updated AttachmentInfo, or an error string on failure.

    """
    query = f"""
    mutation AttachmentCreate($input: AttachmentCreateInput!) {{
        attachmentCreate(input: $input) {{
            success
            attachment {{ {_ATTACHMENT_FIELDS} }}
        }}
    }}
    """
    input_data: dict[str, Any] = {"issueId": issue_id, "url": url}
    if title is not None:
        input_data["title"] = title
    if subtitle is not None:
        input_data["subtitle"] = subtitle
    if icon_url is not None:
        input_data["iconUrl"] = icon_url
    if metadata is not None:
        input_data["metadata"] = metadata
    if create_as_user is not None:
        input_data["createAsUser"] = create_as_user
    if display_icon_url is not None:
        input_data["displayIconUrl"] = display_icon_url

    response: LinearResult = await graphql(query, {"input": input_data})
    if not response.success:
        return response.error or "Failed to create attachment"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    payload = data.get("attachmentCreate")
    if not isinstance(payload, dict) or not payload.get("success"):
        return "Attachment creation failed"
    attachment = payload.get("attachment")
    if not isinstance(attachment, dict):
        return "No attachment in response"
    return _parse_attachment(attachment)


@tool(annotations=ToolAnnotations(readOnlyHint=False))
async def linear_update_attachment(
    attachment_id: str,
    title: str | None = None,
    subtitle: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AttachmentInfo | str:
    """Update an existing attachment by ID.

    Only provided fields are changed; omitted fields remain unchanged.

    Args:
        attachment_id: Attachment UUID.
        title: New display title. Optional.
        subtitle: New display subtitle. Optional.
        metadata: New metadata dict (replaces existing). Optional.

    Returns:
        Updated AttachmentInfo, or an error string on failure.

    """
    query = f"""
    mutation AttachmentUpdate($id: String!, $input: AttachmentUpdateInput!) {{
        attachmentUpdate(id: $id, input: $input) {{
            success
            attachment {{ {_ATTACHMENT_FIELDS} }}
        }}
    }}
    """
    input_data: dict[str, Any] = {}
    if title is not None:
        input_data["title"] = title
    if subtitle is not None:
        input_data["subtitle"] = subtitle
    if metadata is not None:
        input_data["metadata"] = metadata

    response: LinearResult = await graphql(
        query, {"id": attachment_id, "input": input_data}
    )
    if not response.success:
        return response.error or "Failed to update attachment"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    payload = data.get("attachmentUpdate")
    if not isinstance(payload, dict) or not payload.get("success"):
        return "Attachment update failed"
    attachment = payload.get("attachment")
    if not isinstance(attachment, dict):
        return "No attachment in response"
    return _parse_attachment(attachment)


attachment_tools = [
    linear_get_attachment,
    linear_get_attachment_by_url,
    linear_create_attachment,
    linear_update_attachment,
]
