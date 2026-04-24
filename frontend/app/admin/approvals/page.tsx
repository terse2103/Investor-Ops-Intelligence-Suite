export default function ApprovalsPage() {
  return (
    <div style={{ padding: "32px 28px" }}>
      <header style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
          ✅ Approval Center
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          HITL gate for post-call Calendar holds, Sheets rows, and Gmail drafts
        </p>
      </header>

      <div
        className="glass-card"
        style={{ padding: 40, textAlign: "center", maxWidth: 620 }}
      >
        <div style={{ fontSize: 56, marginBottom: 16 }}>✅</div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
          Human-in-the-Loop Approval
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.65, margin: "0 0 20px" }}>
          After each voice booking, three pending actions are queued: a Google Calendar tentative
          hold, a Google Sheets row, and a Gmail draft (with Market Context from the latest pulse).
          No external action fires without admin approval.
        </p>
        <div className="badge badge-warning" style={{ marginBottom: 20 }}>
          ⏳ Coming in Day 5
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
            textAlign: "left",
          }}
        >
          {[
            { icon: "📅", label: "Calendar hold", desc: "Tentative advisor slot via Google Calendar API", type: "calendar" },
            { icon: "📋", label: "Sheets row",    desc: "Booking appended to Advisor Pre-Bookings sheet", type: "sheets" },
            { icon: "📧", label: "Gmail draft",   desc: "Advisor email with Market Context via Gmail MCP", type: "email" },
          ].map((a) => (
            <div
              key={a.type}
              style={{
                background: "var(--bg-muted)",
                borderRadius: 10,
                padding: "12px 16px",
                display: "flex",
                gap: 12,
                alignItems: "center",
              }}
            >
              <span style={{ fontSize: 22, flexShrink: 0 }}>{a.icon}</span>
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{a.label}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{a.desc}</div>
              </div>
              <div className="badge badge-warning" style={{ marginLeft: "auto", flexShrink: 0 }}>
                pending
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
