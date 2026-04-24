"""Google Calendar + Google Sheets API clients. Invoked only post-approval."""

# TODO (Day 5):
#   - OAuth flow using settings.google_client_id / google_client_secret
#   - Token storage + refresh
#   - calendar_create_tentative_hold(topic, code, slot) -> event_id
#   - sheets_append_booking(row) -> None
# Both are invoked only after an admin approves the corresponding pending_action.
