import Link from "next/link";

export default function HomePage() {
  return (
    <main className="flex flex-col min-h-screen" style={{ background: "var(--bg-base)" }}>
      {/* Radial glow blobs */}
      <div
        aria-hidden
        style={{
          position: "fixed",
          top: "-10%",
          left: "20%",
          width: 600,
          height: 600,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(47,100,248,0.15) 0%, transparent 70%)",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />
      <div
        aria-hidden
        style={{
          position: "fixed",
          bottom: "5%",
          right: "10%",
          width: 400,
          height: 400,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(167,139,250,0.1) 0%, transparent 70%)",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      {/* Nav */}
      <nav
        style={{
          position: "relative",
          zIndex: 10,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "20px 40px",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 9,
              background: "linear-gradient(135deg, #2f64f8, #578dff)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 16,
              fontWeight: 700,
              color: "#fff",
              boxShadow: "0 2px 12px rgba(47,100,248,0.4)",
            }}
          >
            IO
          </div>
          <span style={{ fontWeight: 700, fontSize: 15, color: "var(--text-primary)" }}>
            Investor Ops Suite
          </span>
        </div>
        <Link href="/login" className="btn btn-primary" style={{ fontSize: 13, padding: "8px 18px" }}>
          Sign in →
        </Link>
      </nav>

      {/* Hero */}
      <section
        style={{
          position: "relative",
          zIndex: 1,
          flex: 1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "80px 24px 60px",
        }}
      >
        <div className="badge badge-brand" style={{ marginBottom: 24 }}>
          <span>●</span>
          Capstone · INDMoney · RAG + Voice + HITL
        </div>

        <h1
          style={{
            fontSize: "clamp(36px, 6vw, 68px)",
            fontWeight: 800,
            letterSpacing: "-0.03em",
            lineHeight: 1.1,
            maxWidth: 820,
            marginBottom: 22,
            color: "var(--text-primary)",
          }}
        >
          The{" "}
          <span className="gradient-text">Intelligence Suite</span>
          <br />
          for Investor Operations
        </h1>

        <p
          style={{
            fontSize: 18,
            color: "var(--text-secondary)",
            maxWidth: 540,
            lineHeight: 1.7,
            marginBottom: 40,
          }}
        >
          Facts-only mutual fund Q&amp;A · Weekly product pulse from real user
          reviews · Compliant voice booking with HITL approval gates.
        </p>

        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", justifyContent: "center" }}>
          <Link href="/login" className="btn btn-primary" style={{ padding: "13px 32px", fontSize: 15 }}>
            Launch App
          </Link>
          <a
            href="#pillars"
            className="btn btn-ghost"
            style={{ padding: "13px 24px", fontSize: 15 }}
          >
            See how it works
          </a>
        </div>

        {/* Stats strip */}
        <div
          style={{
            marginTop: 70,
            display: "flex",
            gap: 40,
            flexWrap: "wrap",
            justifyContent: "center",
            borderTop: "1px solid var(--border-subtle)",
            paddingTop: 40,
          }}
        >
          {[
            { label: "Eval target", value: "85 / 100" },
            { label: "Safety score", value: "30 / 30" },
            { label: "LLM model", value: "Claude Sonnet 4.6" },
            { label: "Vector store", value: "Chroma + MiniLM" },
          ].map((s) => (
            <div key={s.label} style={{ textAlign: "center" }}>
              <div
                style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "-0.02em" }}
              >
                {s.value}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 3 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Pillars */}
      <section
        id="pillars"
        style={{
          position: "relative",
          zIndex: 1,
          padding: "60px 40px 80px",
          maxWidth: 1100,
          margin: "0 auto",
          width: "100%",
        }}
      >
        <h2
          style={{
            textAlign: "center",
            fontSize: 28,
            fontWeight: 700,
            marginBottom: 48,
            color: "var(--text-primary)",
          }}
        >
          Three pillars, one suite
        </h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 24,
          }}
        >
          {[
            {
              icon: "🧠",
              title: "Pillar A — Smart-Sync KB",
              pill: "M1 + M2",
              desc: "Unified RAG index covering Nippon India mutual fund factsheets and fee explainer docs. Ask any question; get a cited, 3-sentence answer with a source URL.",
              href: "/user/chatbot",
              cta: "Open chatbot",
            },
            {
              icon: "📊",
              title: "Pillar B — Theme-aware Voice",
              pill: "M2 → M3",
              desc: "Weekly pulse clusters Play Store reviews into top themes. The voice agent greets callers with the top theme and books an advisor appointment.",
              href: "/user/voice",
              cta: "Open voice agent",
            },
            {
              icon: "✅",
              title: "Pillar C — HITL Approval Center",
              pill: "M3 + Admin",
              desc: "Post-call actions (Calendar hold, Sheets row, Gmail draft) queue for admin approval. Market context from the latest pulse is injected automatically.",
              cta: "Admin Access Only",
            },
          ].map((p) => (
            <div
              key={p.title}
              className="glass-card"
              style={{ padding: 28, display: "flex", flexDirection: "column", gap: 14 }}
            >
              <div style={{ fontSize: 36 }}>{p.icon}</div>
              <div>
                <span className="badge badge-brand" style={{ marginBottom: 8 }}>
                  {p.pill}
                </span>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                  {p.title}
                </h3>
              </div>
              <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.65, margin: 0 }}>
                {p.desc}
              </p>
              {p.href ? (
                <Link
                  href={p.href}
                  className="btn btn-ghost"
                  style={{ marginTop: "auto", alignSelf: "flex-start", fontSize: 13 }}
                >
                  {p.cta} →
                </Link>
              ) : (
                <span
                  className="btn btn-ghost"
                  style={{ marginTop: "auto", alignSelf: "flex-start", fontSize: 13, opacity: 0.5, cursor: "not-allowed" }}
                >
                  {p.cta}
                </span>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          borderTop: "1px solid var(--border-subtle)",
          padding: "20px 40px",
          textAlign: "center",
          fontSize: 12,
          color: "var(--text-muted)",
          position: "relative",
          zIndex: 1,
        }}
      >
        Investor Ops &amp; Intelligence Suite · Capstone Project · INDMoney ·{" "}
        <a
          href="https://github.com"
          style={{ color: "var(--text-muted)", textDecoration: "underline" }}
        >
          GitHub
        </a>
      </footer>
    </main>
  );
}
