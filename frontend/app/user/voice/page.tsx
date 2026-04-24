export default function VoicePage() {
  return (
    <div style={{ padding: "32px 28px" }}>
      <header style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
          🎙️ Voice Agent
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Book a call with an advisor — themed with today&apos;s top product insights
        </p>
      </header>

      <div
        className="glass-card"
        style={{ padding: 40, textAlign: "center", maxWidth: 520 }}
      >
        <div style={{ fontSize: 56, marginBottom: 16 }}>🎙️</div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
          Theme-aware Voice Booking
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.65, margin: "0 0 20px" }}>
          The Vapi-powered voice agent greets you with the current top 3 review themes,
          walks through a compliant disclaimer, and books an advisor slot. A booking code
          is generated at the end.
        </p>
        <div className="badge badge-warning" style={{ marginBottom: 20 }}>
          ⏳ Coming in Day 4
        </div>
        <div
          style={{
            background: "var(--bg-muted)",
            borderRadius: 10,
            padding: "12px 16px",
            fontSize: 12,
            color: "var(--text-muted)",
            textAlign: "left",
          }}
        >
          <strong style={{ color: "var(--text-secondary)" }}>Flow:</strong> Greet → Disclaimer → Topic →
          Preferred time → 2 available slots → Confirm → Booking code (NL-XXXX)
        </div>
      </div>
    </div>
  );
}
