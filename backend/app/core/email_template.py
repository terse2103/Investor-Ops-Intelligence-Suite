"""Email card renderer shared by the user-facing booking notifier (Resend)
and the advisor Gmail MCP draft.

Returns (html, text) so callers can ship multipart payloads or pick whichever
field the transport supports. All interpolated string values are HTML-escaped
inside `_render_html`; callers pass plain text. The text version is the same
data points laid out as an ASCII card so plaintext-only inboxes still get
something readable.
"""
from __future__ import annotations

from html import escape
from typing import Iterable

# Brand palette (inline; many email clients drop <style> blocks).
_ACCENT = "#0ea5a4"
_BORDER = "#e5e7eb"
_MUTED = "#6b7280"
_TEXT = "#111827"
_BG = "#f3f4f6"
_CANVAS = "#ffffff"
_BODY_BG = "#f9fafb"


def render_card(
    *,
    title: str,
    badge: str | None,
    rows: Iterable[tuple[str, str]],
    body: str | None = None,
    footer: str = "Investor Ops",
) -> tuple[str, str]:
    """Render a branded card as both HTML and plaintext.

    title:  hero text in the header bar (e.g., 'Booking Confirmed').
    badge:  optional secondary chip (booking code, status).
    rows:   ordered (label, value) pairs rendered as a key/value table.
    body:   optional free-form block under the table; styled blockquote
            in HTML, separator-fenced paragraph in plaintext. Newlines
            in body are preserved in both renders.
    footer: signature line.
    """
    row_list = list(rows)
    html_value = _render_html(title, badge, row_list, body, footer)
    text_value = _render_text(title, badge, row_list, body, footer)
    return html_value, text_value


def _render_html(
    title: str,
    badge: str | None,
    rows: list[tuple[str, str]],
    body: str | None,
    footer: str,
) -> str:
    title_h = escape(title)
    badge_html = (
        f'<span style="background:rgba(255,255,255,0.18);'
        f'border:1px solid rgba(255,255,255,0.35);border-radius:9999px;'
        f'padding:4px 12px;display:inline-block;color:#ffffff;'
        f'font-size:12px;font-weight:600;letter-spacing:.04em;">'
        f"{escape(badge)}</span>"
        if badge
        else ""
    )
    rows_html = "\n".join(
        f"<tr>"
        f'<td style="padding:11px 16px;color:{_MUTED};font-size:13px;'
        f'width:38%;border-bottom:1px solid {_BORDER};vertical-align:top;">'
        f"{escape(label)}</td>"
        f'<td style="padding:11px 16px;color:{_TEXT};font-size:14px;'
        f'font-weight:500;border-bottom:1px solid {_BORDER};">'
        f"{escape(value)}</td>"
        f"</tr>"
        for label, value in rows
    )
    body_html = ""
    if body:
        body_html = (
            f'<div style="margin:18px 0 6px;padding:14px 16px;background:{_BODY_BG};'
            f"border-left:3px solid {_ACCENT};border-radius:6px;"
            f'color:{_TEXT};font-size:13px;line-height:1.6;'
            f'white-space:pre-wrap;">{escape(body)}</div>'
        )
    return (
        "<!DOCTYPE html>\n"
        f'<html><body style="margin:0;padding:24px;background:{_BG};'
        f"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        f'Helvetica,Arial,sans-serif;color:{_TEXT};">\n'
        f'  <table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'width="100%" style="max-width:560px;margin:0 auto;background:{_CANVAS};'
        f'border:1px solid {_BORDER};border-radius:10px;overflow:hidden;">\n'
        "    <tr><td>\n"
        f'      <table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'width="100%" style="background:{_ACCENT};">\n'
        "        <tr>\n"
        f'          <td align="left" style="padding:18px 20px;color:#ffffff;'
        f'font-size:16px;font-weight:600;letter-spacing:.01em;">{title_h}</td>\n'
        f'          <td align="right" style="padding:18px 20px;">{badge_html}</td>\n'
        "        </tr>\n"
        "      </table>\n"
        "    </td></tr>\n"
        "    <tr><td style=\"padding:10px 8px 4px;\">\n"
        f'      <table role="presentation" cellpadding="0" cellspacing="0" '
        f'border="0" width="100%">\n        {rows_html}\n      </table>\n'
        f"      {body_html}\n"
        "    </td></tr>\n"
        f'    <tr><td style="padding:14px 20px 18px;color:{_MUTED};font-size:12px;'
        f'border-top:1px solid {_BORDER};">{escape(footer)}</td></tr>\n'
        "  </table>\n"
        "</body></html>"
    )


def _render_text(
    title: str,
    badge: str | None,
    rows: list[tuple[str, str]],
    body: str | None,
    footer: str,
) -> str:
    header = title if not badge else f"{title}  ::  {badge}"
    width = max(len(header) + 4, 50)
    bar = "=" * width
    out: list[str] = [bar, f"  {header}", bar, ""]
    if rows:
        label_w = max(len(label) for label, _ in rows)
        for label, value in rows:
            out.append(f"  {label.ljust(label_w)}  :  {value}")
        out.append("")
    if body:
        thin = "-" * width
        out.append(thin)
        for ln in body.splitlines():
            out.append(f"  {ln}" if ln.strip() else "")
        out.append(thin)
        out.append("")
    out.append(f"-- {footer}")
    return "\n".join(out)
