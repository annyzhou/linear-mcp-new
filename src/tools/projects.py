# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Project tools.

Tools:
  linear_get_project     -- get project by ID
  linear_list_projects   -- list projects with optional filter
  linear_create_project  -- create a new project
  linear_update_project  -- update an existing project
"""

from __future__ import annotations

from typing import Any

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from linear.request import _float, _opt_str, _str, graphql
from linear.types import JSONObject, LinearResult, ProjectInfo


# --- Fragments ---

_PROJECT_FIELDS = """
    id name state progress targetDate
"""


# --- Helpers ---


def _parse_project(raw: JSONObject) -> ProjectInfo:
    """Parse a raw GraphQL project node into a ProjectInfo.

    Args:
        raw: Untyped project node from a GraphQL response.

    Returns:
        Parsed ProjectInfo with coerced fields.

    """
    result = ProjectInfo(
        id=_str(raw.get("id")),
        name=_str(raw.get("name")),
        state=_opt_str(raw.get("state")),
        progress=_float(raw.get("progress")),
        target_date=_opt_str(raw.get("targetDate")),
    )
    return result


# --- Tools ---


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_get_project(project_id: str) -> ProjectInfo | str:
    """Fetch a project by ID.

    Args:
        project_id: Project UUID.

    Returns:
        ProjectInfo, or an error string on failure.

    """
    query = f"""
    query Project($id: String!) {{
        project(id: $id) {{ {_PROJECT_FIELDS} }}
    }}
    """
    response: LinearResult = await graphql(query, {"id": project_id})
    if not response.success:
        return response.error or "Failed to fetch project"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    project_data = data.get("project")
    if not isinstance(project_data, dict):
        return "Project not found"
    result = _parse_project(project_data)
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_list_projects(
    filter: JSONObject | None = None,
    first: int = 50,
    after: str | None = None,
    include_archived: bool = False,
) -> list[ProjectInfo] | str:
    """List projects with optional GraphQL filter passthrough.

    Args:
        filter: Raw GraphQL ProjectFilter dictionary. Passed through as-is.
        first: Maximum number of projects to return.
        after: Cursor for pagination (from a previous response).
        include_archived: Include archived projects in results.

    Returns:
        List of ProjectInfo objects, or an error string on failure.

    """
    query = f"""
    query Projects(
        $filter: ProjectFilter,
        $first: Int,
        $after: String,
        $includeArchived: Boolean
    ) {{
        projects(
            filter: $filter,
            first: $first,
            after: $after,
            includeArchived: $includeArchived
        ) {{
            nodes {{ {_PROJECT_FIELDS} }}
            pageInfo {{ hasNextPage endCursor }}
        }}
    }}
    """
    variables: dict[str, Any] = {
        "filter": filter,
        "first": first,
        "after": after,
        "includeArchived": include_archived,
    }
    response: LinearResult = await graphql(query, variables)
    if not response.success:
        return response.error or "Failed to list projects"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    projects_data = data.get("projects")
    if not isinstance(projects_data, dict):
        return "No projects data"
    nodes = projects_data.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    result = [_parse_project(node) for node in nodes if isinstance(node, dict)]
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=False))
async def linear_create_project(
    name: str,
    team_ids: list[str] | None = None,
    description: str | None = None,
    state: str | None = None,
    target_date: str | None = None,
) -> ProjectInfo | str:
    """Create a new project.

    Args:
        name: Project name.
        team_ids: Team UUIDs to associate with the project. Optional.
        description: Markdown description. Optional.
        state: Initial state (planned, started, paused, completed, cancelled).
        target_date: ISO-8601 target completion date. Optional.

    Returns:
        Created ProjectInfo, or an error string on failure.

    """
    query = f"""
    mutation ProjectCreate($input: ProjectCreateInput!) {{
        projectCreate(input: $input) {{
            success
            project {{ {_PROJECT_FIELDS} }}
        }}
    }}
    """
    input_data: dict[str, Any] = {"name": name}
    if team_ids is not None:
        input_data["teamIds"] = team_ids
    if description is not None:
        input_data["description"] = description
    if state is not None:
        input_data["state"] = state
    if target_date is not None:
        input_data["targetDate"] = target_date

    response: LinearResult = await graphql(query, {"input": input_data})
    if not response.success:
        return response.error or "Failed to create project"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    payload = data.get("projectCreate")
    if not isinstance(payload, dict) or not payload.get("success"):
        return "Project creation failed"
    project_data = payload.get("project")
    if not isinstance(project_data, dict):
        return "No project in response"
    result = _parse_project(project_data)
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=False))
async def linear_update_project(
    project_id: str,
    name: str | None = None,
    description: str | None = None,
    state: str | None = None,
    target_date: str | None = None,
) -> ProjectInfo | str:
    """Update an existing project.

    Only provided fields are modified; omitted fields are left unchanged.

    Args:
        project_id: Project UUID.
        name: New name. Optional.
        description: New markdown description. Optional.
        state: New state (planned, started, paused, completed, cancelled).
        target_date: New ISO-8601 target date. Optional.

    Returns:
        Updated ProjectInfo, or an error string on failure.

    """
    query = f"""
    mutation ProjectUpdate($id: String!, $input: ProjectUpdateInput!) {{
        projectUpdate(id: $id, input: $input) {{
            success
            project {{ {_PROJECT_FIELDS} }}
        }}
    }}
    """
    input_data: dict[str, Any] = {}
    if name is not None:
        input_data["name"] = name
    if description is not None:
        input_data["description"] = description
    if state is not None:
        input_data["state"] = state
    if target_date is not None:
        input_data["targetDate"] = target_date

    if not input_data:
        return "No fields to update"

    response: LinearResult = await graphql(
        query, {"id": project_id, "input": input_data}
    )
    if not response.success:
        return response.error or "Failed to update project"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    payload = data.get("projectUpdate")
    if not isinstance(payload, dict) or not payload.get("success"):
        return "Project update failed"
    project_data = payload.get("project")
    if not isinstance(project_data, dict):
        return "No project in response"
    result = _parse_project(project_data)
    return result


project_tools = [
    linear_get_project,
    linear_list_projects,
    linear_create_project,
    linear_update_project,
]
