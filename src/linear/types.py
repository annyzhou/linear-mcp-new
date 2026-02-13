# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Typed models for Linear API responses.

Result types (frozen dataclasses):
  LinearResult         -- raw GraphQL result wrapper
  TeamInfo             -- team summary
  UserInfo             -- user profile
  WorkflowStateInfo    -- workflow state (issue status)
  LabelInfo            -- issue label
  IssueInfo            -- issue summary
  CommentInfo          -- issue comment
  ProjectInfo          -- project summary
  CycleInfo            -- cycle summary
  AttachmentInfo       -- issue attachment (external link)
  IssueContextInfo     -- compound: issue + comments + team states

Type aliases:
  JSONPrimitive        -- scalar JSON values
  JSONValue            -- recursive JSON value (pre-3.12 TypeAlias)
  JSONObject           -- dict[str, JSONValue]
  JSONArray            -- list[JSONValue]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias


# --- JSON types ---

JSONPrimitive: TypeAlias = str | int | float | bool | None
"""Scalar JSON values. Non-recursive, safe as plain union."""

JSONValue: TypeAlias = str | int | float | bool | dict[str, Any] | list[Any] | None
"""Recursive JSON value: primitive, object, or array.

Cannot be truly recursive with TypeAlias (pre-3.12); uses Any for nesting.
PEP 695 ``type`` statements (3.12+) resolve this via lazy evaluation.
"""

JSONObject: TypeAlias = dict[str, JSONValue]
"""JSON object: string keys mapped to JSON values."""

JSONArray: TypeAlias = list[JSONValue]
"""JSON array: ordered sequence of JSON values."""


# --- Generic result ---


@dataclass(frozen=True, slots=True)
class LinearResult:
    """Raw Linear GraphQL result.

    Used for mutations that don't produce structured output
    and as the internal request return type.
    """

    # fmt: off
    success: bool
    data:    JSONValue | None = None
    error:   str | None       = None
    # fmt: on


# --- Teams ---


@dataclass(frozen=True, slots=True)
class TeamInfo:
    """Team summary."""

    # fmt: off
    id:   str
    name: str
    key:  str
    # fmt: on


# --- Users ---


@dataclass(frozen=True, slots=True)
class UserInfo:
    """User profile."""

    # fmt: off
    id:    str
    name:  str
    email: str | None = None
    # fmt: on


# --- Workflow States ---


@dataclass(frozen=True, slots=True)
class WorkflowStateInfo:
    """Workflow state (issue status).

    Linear issues are assigned a state from a team's workflow.
    Types: backlog, unstarted, started, completed, cancelled.
    """

    # fmt: off
    id:       str
    name:     str
    type:     str                  # backlog | unstarted | started | completed | cancelled
    color:    str | None = None
    position: float      = 0.0
    # fmt: on


# --- Labels ---


@dataclass(frozen=True, slots=True)
class LabelInfo:
    """Issue label."""

    # fmt: off
    id:    str
    name:  str
    color: str | None = None
    # fmt: on


# --- Issues ---


@dataclass(frozen=True, slots=True)
class IssueInfo:
    """Issue summary."""

    # fmt: off
    id:          str
    identifier:  str                           # e.g. "ENG-123"
    title:       str
    description: str | None        = None      # populated for single-issue fetches, omitted from lists
    state:       str | None        = None
    priority:    int                = 0         # 0=none, 1=urgent, 2=high, 3=medium, 4=low
    assignee:    str | None        = None
    labels:      list[str]         = field(default_factory=list)
    created_at:  str | None        = None
    updated_at:  str | None        = None
    # fmt: on


# --- Comments ---


@dataclass(frozen=True, slots=True)
class CommentInfo:
    """Issue comment."""

    # fmt: off
    id:         str
    body:       str
    user:       str | None = None
    created_at: str | None = None
    # fmt: on


# --- Projects ---


@dataclass(frozen=True, slots=True)
class ProjectInfo:
    """Project summary."""

    # fmt: off
    id:          str
    name:        str
    state:       str | None = None      # planned | started | paused | completed | cancelled
    progress:    float      = 0.0
    target_date: str | None = None
    # fmt: on


# --- Cycles ---


@dataclass(frozen=True, slots=True)
class CycleInfo:
    """Cycle summary."""

    # fmt: off
    id:        str
    number:    int
    name:      str | None = None
    starts_at: str | None = None
    ends_at:   str | None = None
    progress:  float      = 0.0
    # fmt: on


# --- Attachments ---


@dataclass(frozen=True, slots=True)
class AttachmentInfo:
    """Issue attachment (external link).

    Attachments link external resources to issues.  The ``url`` field is
    idempotent per-issue: re-creating with the same URL updates instead.
    """

    # fmt: off
    id:       str
    url:      str
    title:    str | None = None
    subtitle: str | None = None
    # fmt: on


# --- Compound types ---


@dataclass(frozen=True, slots=True)
class IssueContextInfo:
    """Full context for an issue: details, discussion, and available states.

    Compound response from ``linear_issue_context`` — aggregates issue details,
    comments, and the team's workflow states into a single GraphQL round-trip.
    """

    # fmt: off
    issue:    IssueInfo
    comments: list[CommentInfo]        = field(default_factory=list)
    states:   list[WorkflowStateInfo]  = field(default_factory=list)
    # fmt: on
