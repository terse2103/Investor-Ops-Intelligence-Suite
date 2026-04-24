"""Transactional email dispatch for booking-decision notifications."""

# TODO (Day 5): implement send_booking_decision(user_id, call_id, decision).
# Reads user_contacts at dispatch time (not at booking time). Writes a
# notifications_sent audit row on every attempt. Provider-agnostic adapter.
