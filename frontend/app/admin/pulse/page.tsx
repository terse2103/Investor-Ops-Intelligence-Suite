export default function PulsePage() {
  return (
    <div style={{ padding: "32px 28px" }}>
      <header style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
          📊 Weekly Product Pulse
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Scraped Play Store review themes, top quotes, and action ideas
        </p>
      </header>

      <div
        className="glass-card"
        style={{ padding: 40, textAlign: "center", maxWidth: 620 }}
      >
        <div style={{ fontSize: 56, marginBottom: 16 }}>📊</div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 10px" }}>
          AI-generated weekly pulse
        </h2>
        <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.65, margin: "0 0 20px" }}>
          Every week, the scraper fetches recent INDMoney Play Store reviews. Claude clusters them
          into up to 5 themes, surfaces the top 3, picks 3 verbatim quotes, and writes a ≤250-word
          pulse with exactly 3 action ideas.
        </p>
        <div className="badge badge-warning" style={{ marginBottom: 20 }}>
          ⏳ Coming in Day 3
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 12,
            textAlign: "left",
          }}
        >
          {[
            { icon: "🔍", label: "Themes", desc: "Max 5, top 3 surfaced" },
            { icon: "💬", label: "Quotes", desc: "Exactly 3 verbatim" },
            { icon: "📝", label: "Pulse note", desc: "≤250 words" },
            { icon: "🎯", label: "Action ideas", desc: "Exactly 3" },
          ].map((f) => (
            <div
              key={f.label}
              style={{
                background: "var(--bg-muted)",
                borderRadius: 10,
                padding: "12px 14px",
              }}
            >
              <div style={{ fontSize: 20, marginBottom: 4 }}>{f.icon}</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{f.label}</div>
              <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
