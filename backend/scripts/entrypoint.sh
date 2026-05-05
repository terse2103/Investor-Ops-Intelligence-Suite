#!/bin/sh
# Container entrypoint for HF Spaces deployment.
#
# Materializes Gmail MCP OAuth credentials from HF Space secrets (env vars)
# into ~/.gmail-mcp/ so the @gongrzhe/server-gmail-autoauth-mcp subprocess
# (spawned by app.core.mcp_client) can read them at draft-creation time.
#
# Required HF Space secrets when GMAIL_MCP_COMMAND is set:
#   GMAIL_OAUTH_KEYS_JSON         - content of gcp-oauth.keys.json
#   GMAIL_OAUTH_CREDENTIALS_JSON  - content of credentials.json (post-OAuth tokens)
#
# Generate both locally with `npx -y @gongrzhe/server-gmail-autoauth-mcp auth`
# and paste their contents into the HF Space secrets UI.
set -e

if [ -n "$GMAIL_OAUTH_KEYS_JSON" ] || [ -n "$GMAIL_OAUTH_CREDENTIALS_JSON" ]; then
  mkdir -p "$HOME/.gmail-mcp"

  if [ -n "$GMAIL_OAUTH_KEYS_JSON" ]; then
    printf '%s' "$GMAIL_OAUTH_KEYS_JSON" > "$HOME/.gmail-mcp/gcp-oauth.keys.json"
    chmod 600 "$HOME/.gmail-mcp/gcp-oauth.keys.json"
    bytes=$(wc -c < "$HOME/.gmail-mcp/gcp-oauth.keys.json")
    echo "[entrypoint] wrote $HOME/.gmail-mcp/gcp-oauth.keys.json ($bytes bytes)" >&2
  fi

  if [ -n "$GMAIL_OAUTH_CREDENTIALS_JSON" ]; then
    printf '%s' "$GMAIL_OAUTH_CREDENTIALS_JSON" > "$HOME/.gmail-mcp/credentials.json"
    chmod 600 "$HOME/.gmail-mcp/credentials.json"
    bytes=$(wc -c < "$HOME/.gmail-mcp/credentials.json")
    echo "[entrypoint] wrote $HOME/.gmail-mcp/credentials.json ($bytes bytes)" >&2
  fi
else
  echo "[entrypoint] GMAIL_OAUTH_*_JSON not set; MCP draft path will skip cleanly" >&2
fi

exec uv run uvicorn app.main:app --host 0.0.0.0 --port 7860
