# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Cycle tools.

Tools:
  linear_list_cycles   -- list cycles for a team
  linear_get_cycle     -- get a cycle by ID
  linear_active_cycle  -- get the current active cycle for a team
"""

from __future__ import annotations

from dedalus_mcp import tool
from dedalus_mcp.types import ToolAnnotations

from linear.request import _float, _int, _opt_str, _str, graphql
from linear.types import CycleInfo, JSONObject, LinearResult


# --- Fragments ---

_CYCLE_FIELDS = """
    id number name startsAt endsAt progress
"""


# --- Helpers ---


def _parse_cycle(raw: JSONObject) -> CycleInfo:
    """Parse a raw GraphQL cycle node into a CycleInfo.

    Args:
        raw: Untyped cycle node from a GraphQL response.

    Returns:
        Parsed CycleInfo with coerced fields.

    """
    result = CycleInfo(
        id=_str(raw.get("id")),
        number=_int(raw.get("number")),
        name=_opt_str(raw.get("name")),
        starts_at=_opt_str(raw.get("startsAt")),
        ends_at=_opt_str(raw.get("endsAt")),
        progress=_float(raw.get("progress")),
    )
    return result


# --- Tools ---


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_list_cycles(
    team_id: str,
    first: int = 25,
    after: str | None = None,
    include_archived: bool = False,
) -> list[CycleInfo] | str:
    """List cycles for a team.

    Args:
        team_id: Team UUID.
        first: Maximum number of cycles to return.
        after: Cursor for pagination (from a previous response).
        include_archived: Include archived cycles in results.

    Returns:
        List of CycleInfo objects, or an error string on failure.

    """
    query = f"""
    query TeamCycles($id: String!, $first: Int, $after: String, $includeArchived: Boolean) {{
        team(id: $id) {{
            cycles(first: $first, after: $after, includeArchived: $includeArchived) {{
                nodes {{ {_CYCLE_FIELDS} }}
                pageInfo {{ hasNextPage endCursor }}
            }}
        }}
    }}
    """
    variables = {
        "id": team_id,
        "first": first,
        "after": after,
        "includeArchived": include_archived,
    }
    response: LinearResult = await graphql(query, variables)
    if not response.success:
        return response.error or "Failed to list cycles"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    team_data = data.get("team")
    if not isinstance(team_data, dict):
        return "Team not found"
    cycles_data = team_data.get("cycles")
    if not isinstance(cycles_data, dict):
        return "No cycles data"
    nodes = cycles_data.get("nodes", [])
    if not isinstance(nodes, list):
        return "Unexpected nodes format"
    result = [_parse_cycle(node) for node in nodes if isinstance(node, dict)]
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_get_cycle(cycle_id: str) -> CycleInfo | str:
    """Fetch a cycle by ID.

    Args:
        cycle_id: Cycle UUID.

    Returns:
        CycleInfo, or an error string on failure.

    """
    query = f"""
    query Cycle($id: String!) {{
        cycle(id: $id) {{ {_CYCLE_FIELDS} }}
    }}
    """
    response: LinearResult = await graphql(query, {"id": cycle_id})
    if not response.success:
        return response.error or "Failed to fetch cycle"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    cycle_data = data.get("cycle")
    if not isinstance(cycle_data, dict):
        return "Cycle not found"
    result = _parse_cycle(cycle_data)
    return result


@tool(annotations=ToolAnnotations(readOnlyHint=True))
async def linear_active_cycle(team_id: str) -> CycleInfo | str:
    """Fetch the current active cycle for a team.

    Returns the team's ``activeCycle`` if one exists.

    Args:
        team_id: Team UUID.

    Returns:
        CycleInfo for the active cycle, or an error string if none exists
        or on failure.

    """
    query = f"""
    query ActiveCycle($id: String!) {{
        team(id: $id) {{
            activeCycle {{ {_CYCLE_FIELDS} }}
        }}
    }}
    """
    response: LinearResult = await graphql(query, {"id": team_id})
    if not response.success:
        return response.error or "Failed to fetch active cycle"
    data = response.data
    if not isinstance(data, dict):
        return "Unexpected response"
    team_data = data.get("team")
    if not isinstance(team_data, dict):
        return "Team not found"
    cycle_data = team_data.get("activeCycle")
    if not isinstance(cycle_data, dict):
        return "No active cycle"
    result = _parse_cycle(cycle_data)
    return result


cycle_tools = [
    linear_list_cycles,
    linear_get_cycle,
    linear_active_cycle,
]
