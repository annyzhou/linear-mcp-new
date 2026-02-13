# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Team tools.

Tools:
  linear_list_teams        -- list all teams in the workspace
  linear_get_team          -- get a team by ID
  linear_list_team_states  -- list workflow states for a team
"""

from __future__ import annotations

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from linear.request import _float, _opt_str, _str, graphql
from linear.types import JSONObject, LinearResult, TeamInfo, WorkflowStateInfo


# --- Helpers ---


def _parse_team(raw: JSONObject) -> TeamInfo:
    """Parse a raw GraphQL team node into a TeamInfo.

    Args:
        raw: Untyped team node from a GraphQL response.

    Returns:
        Parsed TeamInfo with coerced fields.

    """
    result = TeamInfo(
        id=_str(raw.get("id")),
        name=_str(raw.get("name")),
        key=_str(raw.get("key")),
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
async def linear_list_teams(
    first: int = 50,
    after: str | None = None,
) -> list[TeamInfo] | str:
    """List all teams in the workspace.

    Args:
        first: Maximum number of teams to return.
        after: Cursor for pagination (from a previous response).

    Returns:
        List of TeamInfo objects, or an error string on failure.

    """
    query = """
    query Teams($first: Int, $after: String) {
        teams(first: $first, after: $after) {
            nodes { id name key }
            pageInfo { hasNextPage endCursor }
        }
    }
    """
    response: LinearResult = await graphql(query, {"first": first, "after": after})
    if not response.success:
        return response.error or "Failed to list teams"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    teams_data = data.get("teams")
    if not isinstance(teams_data, dict):
        return "No teams data"
    nodes = teams_data.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    result = [_parse_team(node) for node in nodes if isinstance(node, dict)]
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_get_team(team_id: str) -> TeamInfo | str:
    """Fetch a team by ID.

    Args:
        team_id: Team UUID.

    Returns:
        TeamInfo, or an error string on failure.

    """
    query = """
    query Team($id: String!) {
        team(id: $id) { id name key }
    }
    """
    response: LinearResult = await graphql(query, {"id": team_id})
    if not response.success:
        return response.error or "Failed to fetch team"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    team_data = data.get("team")
    if not isinstance(team_data, dict):
        return "Team not found"
    result = _parse_team(team_data)
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_list_team_states(team_id: str) -> list[WorkflowStateInfo] | str:
    """List workflow states (statuses) for a team.

    Essential for creating or updating issues — Linear requires a valid
    state UUID, not a free-text status string.

    Args:
        team_id: Team UUID.

    Returns:
        List of WorkflowStateInfo sorted by position, or an error string
        on failure.

    """
    query = """
    query TeamStates($id: String!) {
        team(id: $id) {
            states {
                nodes { id name type color position }
            }
        }
    }
    """
    response: LinearResult = await graphql(query, {"id": team_id})
    if not response.success:
        return response.error or "Failed to fetch team states"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    team_data = data.get("team")
    if not isinstance(team_data, dict):
        return "Team not found"
    states_data = team_data.get("states")
    if not isinstance(states_data, dict):
        return "No states data"
    nodes = states_data.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    result = [_parse_state(node) for node in nodes if isinstance(node, dict)]
    return result


team_tools = [
    linear_list_teams,
    linear_get_team,
    linear_list_team_states,
]
