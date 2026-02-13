# linear-mcp

A [Linear](https://linear.app) MCP server built on the [Dedalus](https://dedaluslabs.ai) platform.

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)
- A Linear workspace with an OAuth2 application
- A [Dedalus](https://dedaluslabs.ai) account

---

## Quick Start

### 1. Create a Linear OAuth Application

1. Go to **Linear → Settings → API → OAuth2 Applications** ([link](https://linear.app/settings/api/applications)).
2. Create a new application.
3. Under **Redirect URIs**, add:
   ```
   https://as.dedaluslabs.ai/oauth/callback
   ```
4. Note the **Client ID** and **Client Secret**.

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Fill in your `.env`:

```env
# Linear OAuth (consumed by the Dedalus platform during deployment)
OAUTH_ENABLED=true
OAUTH_AUTHORIZE_URL=https://linear.app/oauth/authorize
OAUTH_TOKEN_URL=https://api.linear.app/oauth/token
OAUTH_CLIENT_ID=<your-linear-client-id>
OAUTH_CLIENT_SECRET=<your-linear-client-secret>
OAUTH_SCOPES_AVAILABLE=read,write,issues:create,comments:create
OAUTH_BASE_URL=https://api.linear.app

# Dedalus Platform (for the sample client)
DEDALUS_API_KEY=<your-dedalus-api-key>
DEDALUS_API_URL=https://api.dedaluslabs.ai
DEDALUS_AS_URL=https://as.dedaluslabs.ai

# After deploying, set this to your slug
LINEAR_MCP_SLUG=your-org/linear-mcp
```

### 3. Deploy to Dedalus

1. Log in to the [Dedalus Dashboard](https://dedaluslabs.ai).
2. Go to **Add Server** and connect this GitHub repository.
3. In the server configuration, enter the environment variables from your `.env` (`OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, etc.).
4. Deploy. The dashboard will show your server slug (e.g. `your-org/linear-mcp`).

### 4. Install Dependencies

```bash
uv sync
```

### 5. Run the Client

```bash
uv run src/_client.py
```

On first use, the client will open your browser for Linear OAuth authorization.
After completing the flow, you can interact with Linear through the agent.

```
=== Linear MCP Agent ===
Server: your-org/linear-mcp
Type 'quit' or 'exit' to end the session.

You: What issues are assigned to me?
Assistant: ...
```

---

## Environment Variables

### Linear OAuth (server-side, set during Dedalus deployment)

| Variable | Description |
| --- | --- |
| `OAUTH_ENABLED` | `true` |
| `OAUTH_AUTHORIZE_URL` | `https://linear.app/oauth/authorize` |
| `OAUTH_TOKEN_URL` | `https://api.linear.app/oauth/token` |
| `OAUTH_CLIENT_ID` | Your Linear OAuth app client ID |
| `OAUTH_CLIENT_SECRET` | Your Linear OAuth app client secret |
| `OAUTH_SCOPES_AVAILABLE` | `read,write,issues:create,comments:create` |
| `OAUTH_BASE_URL` | `https://api.linear.app` |

### Dedalus Platform (client-side, for `_client.py`)

| Variable | Description |
| --- | --- |
| `DEDALUS_API_KEY` | Your Dedalus API key (`dsk_*`) |
| `DEDALUS_API_URL` | API base URL (default: `https://api.dedaluslabs.ai`) |
| `DEDALUS_AS_URL` | Authorization server URL (default: `https://as.dedaluslabs.ai`) |
---

## Running the Server Locally

```bash
uv run src/main.py
```

This starts the MCP server on port 8080. Note that `_client.py` always connects
through Dedalus (not localhost). Use this for local testing with a direct MCP client.

---

## Lint & Typecheck

```bash
uv run --group lint ruff format src/
uv run --group lint ruff check src/ --fix
uv run --group lint ty check src/
```

---

## Available Tools

| Tool | R/W | Description |
| --- | --- | --- |
| `linear_get_issue` | R | Get issue by ID or identifier (ENG-123) |
| `linear_list_issues` | R | List issues with filters |
| `linear_create_issue` | W | Create a new issue |
| `linear_update_issue` | W | Update an existing issue |
| `linear_list_comments` | R | List comments on an issue |
| `linear_create_comment` | W | Add a comment to an issue |
| `linear_get_project` | R | Get project by ID |
| `linear_list_projects` | R | List projects |
| `linear_create_project` | W | Create a new project |
| `linear_update_project` | W | Update an existing project |
| `linear_list_cycles` | R | List cycles for a team |
| `linear_get_cycle` | R | Get a cycle by ID |
| `linear_active_cycle` | R | Get the current active cycle for a team |
| `linear_list_teams` | R | List all teams |
| `linear_get_team` | R | Get a team by ID |
| `linear_list_team_states` | R | List workflow states (statuses) for a team |
| `linear_whoami` | R | Get authenticated user profile |
| `linear_list_users` | R | List workspace members |
| `linear_list_labels` | R | List labels |
| `linear_create_label` | W | Create a new label |
| `linear_search_issues` | R | Full-text search across issues |
| `linear_issue_context` | R | Full issue context (details + comments + states) |
| `linear_my_issues` | R | Issues assigned to the authenticated user |
| `linear_get_attachment` | R | Get an attachment by ID |
| `linear_get_attachment_by_url` | R | Get an attachment by URL |
| `linear_create_attachment` | W | Create an attachment on an issue |
| `linear_update_attachment` | W | Update an existing attachment |

---

## Architecture

Linear uses a single GraphQL endpoint (`POST /graphql`). The request layer
dispatches queries through the Dedalus HTTP enclave, which injects OAuth
credentials transparently.

```
src/
├── linear/
│   ├── config.py      # Connection definition (OAuth)
│   ├── request.py     # GraphQL dispatch + coercion helpers
│   └── types.py       # Typed dataclass models
├── tools/
│   ├── issues.py      # Issue CRUD
│   ├── comments.py    # Comment operations
│   ├── projects.py    # Project CRUD
│   ├── cycles.py      # Cycle queries
│   ├── teams.py       # Team + workflow states
│   ├── users.py       # User queries
│   ├── labels.py      # Label operations
│   ├── search.py      # Issue search
│   ├── attachments.py # Attachment operations
│   └── compound.py    # Multi-step workflows (issue context, my issues)
├── server.py          # MCPServer setup
├── main.py            # Server entry point
└── _client.py         # Interactive agent client (DAuth)
```

---

## Troubleshooting

### "Linear MCP server is currently unavailable"

The client asks the Dedalus platform to route to your MCP server by slug. This
error means the platform cannot reach it. Common causes:

1. **Server not deployed** — Deploy this repo from the Dedalus Dashboard first.
2. **Wrong slug** — Verify `LINEAR_MCP_SLUG` matches your deployment.
3. **OAuth not completed** — Complete the Linear OAuth flow when prompted.

### "Invalid redirect_uri parameter for the application"

Linear's OAuth rejected the callback URL. Fix by adding `https://as.dedaluslabs.ai/oauth/callback`
to your Linear OAuth app's **Redirect URIs** in
[Linear Settings → API → OAuth2 Applications](https://linear.app/settings/api/applications).

### OAuth re-authorization after redeployment

Redeploying the server may generate a new server ID, invalidating previous OAuth
tokens. If you see a 401 error after redeploying, run the client again and
complete the OAuth flow when prompted.

---

## Notes

- Linear's API is GraphQL-only. Every tool dispatches a GraphQL query or mutation.
- Workflow states vary per team. Use `linear_list_team_states` to discover valid
  state IDs before creating or transitioning issues.
- Issue identifiers (e.g. `ENG-123`) can be used interchangeably with UUIDs.
- Priority values: 0 = No priority, 1 = Urgent, 2 = High, 3 = Medium, 4 = Low.
- Archived resources are hidden by default; some tools accept `include_archived`.
- Authentication uses OAuth2 via DAuth. Personal API keys are not supported.
