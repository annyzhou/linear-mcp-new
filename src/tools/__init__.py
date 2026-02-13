# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Tool registry for linear-mcp.

Modules:
  issues      -- linear_get_issue, linear_list_issues, linear_create_issue, linear_update_issue
  comments    -- linear_list_comments, linear_create_comment
  projects    -- linear_get_project, linear_list_projects, linear_create_project, linear_update_project
  cycles      -- linear_list_cycles, linear_get_cycle, linear_active_cycle
  teams       -- linear_list_teams, linear_get_team, linear_list_team_states
  users       -- linear_whoami, linear_list_users
  labels      -- linear_list_labels, linear_create_label
  search      -- linear_search_issues
  attachments -- linear_get_attachment, linear_get_attachment_by_url, linear_create_attachment, linear_update_attachment
  compound    -- linear_issue_context, linear_my_issues
"""

from __future__ import annotations

from tools.attachments import attachment_tools
from tools.comments import comment_tools
from tools.compound import compound_tools
from tools.cycles import cycle_tools
from tools.issues import issue_tools
from tools.labels import label_tools
from tools.projects import project_tools
from tools.search import search_tools
from tools.teams import team_tools
from tools.users import user_tools


linear_tools = [
    *issue_tools,
    *comment_tools,
    *project_tools,
    *cycle_tools,
    *team_tools,
    *user_tools,
    *label_tools,
    *search_tools,
    *attachment_tools,
    *compound_tools,
]
