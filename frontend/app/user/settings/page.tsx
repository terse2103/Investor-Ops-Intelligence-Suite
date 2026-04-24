export default function SettingsPage() {
  return (
    <div style={{ padding: "32px 28px" }}>
      <header style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
          ⚙️ Settings
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Notification email used when the admin approves or rejects your booking
        </p>
      </header>

      <div
        className="glass-card"
        style={{ padding: 40, textAlign: "center", maxWidth: 520 }}
      >
        <div style={{ fontSize: 48, marginBottom: 14 }}>📧</div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
          Notification Email
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.65, margin: "0 0 20px" }}>
          Save your email address here. The ops suite will send you one notification
          when an admin approves or rejects your advisor booking.
        </p>
        <div className="badge badge-warning">⏳ Coming in Day 5</div>
      </div>
    </div>
  );
}
