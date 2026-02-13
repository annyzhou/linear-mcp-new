# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Linear connection configuration.

Evaluated at import time, after ``load_dotenv()`` in ``main.py``
has already injected the .env file.

Linear uses OAuth2 for authentication. The Dedalus platform handles
token exchange; the server only declares the secret name it expects.

Objects:
  linear -- Connection with OAuth bearer token auth
"""

from __future__ import annotations

from dedalus_mcp.auth import Connection, SecretKeys


linear = Connection(
    name="linear-mcp",
    secrets=SecretKeys(token="LINEAR_ACCESS_TOKEN"),  # noqa: S106
    base_url="https://api.linear.app",
    auth_header_format="Bearer {api_key}",
)
