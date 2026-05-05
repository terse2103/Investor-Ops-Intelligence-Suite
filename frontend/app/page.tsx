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

        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", justifyContent: "center", marginTop: 40 }}>
          <Link href="/login" className="btn btn-primary" style={{ padding: "13px 32px", fontSize: 15 }}>
            Launch App
          </Link>
          <a
            href="#features"
            className="btn btn-ghost"
            style={{ padding: "13px 24px", fontSize: 15 }}
          >
            See how it works
          </a>
        </div>

      </section>

      {/* Features */}
      <section
        id="features"
        style={{
          position: "relative",
          zIndex: 1,
          padding: "60px 40px 80px",
          maxWidth: 1100,
          margin: "0 auto",
          width: "100%",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <div
            style={{
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "0.18em",
              textTransform: "uppercase",
              color: "var(--text-muted)",
              marginBottom: 10,
            }}
          >
            Key Features
          </div>
          <h2
            style={{
              fontSize: 32,
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: "var(--text-primary)",
              margin: 0,
            }}
          >
            Everything you need, in one suite
          </h2>
        </div>

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
              accent: "linear-gradient(135deg, rgba(47,100,248,0.18), rgba(87,141,255,0.05))",
              title: "Smart-Sync Knowledge Base",
              desc: "Unified RAG index covering Nippon India mutual fund factsheets and fee explainer docs. Ask any question; get a cited, 3-sentence answer with a source URL.",
              href: "/user/chatbot",
              cta: "Open chatbot",
            },
            {
              icon: "📊",
              accent: "linear-gradient(135deg, rgba(167,139,250,0.20), rgba(167,139,250,0.05))",
              title: "Theme-aware Voice Agent",
              desc: "Weekly pulse clusters Play Store reviews into top themes. The voice agent greets callers with the top theme and books an advisor appointment.",
              href: "/user/voice",
              cta: "Open voice agent",
            },
            {
              icon: "✅",
              accent: "linear-gradient(135deg, rgba(74,222,128,0.18), rgba(74,222,128,0.04))",
              title: "HITL Approval Center",
              desc: "Post-call actions (Calendar hold, Sheets row, Gmail draft) queue for admin approval. Market context from the latest pulse is injected automatically.",
              cta: "Admin Access Only",
            },
          ].map((p) => (
            <div
              key={p.title}
              className="glass-card feature-card"
              style={{
                padding: 30,
                display: "flex",
                flexDirection: "column",
                gap: 16,
                position: "relative",
                overflow: "hidden",
              }}
            >
              <div
                aria-hidden
                style={{
                  position: "absolute",
                  top: -40,
                  right: -40,
                  width: 160,
                  height: 160,
                  borderRadius: "50%",
                  background: p.accent,
                  filter: "blur(20px)",
                  pointerEvents: "none",
                }}
              />
              <div
                style={{
                  width: 52,
                  height: 52,
                  borderRadius: 12,
                  background: p.accent,
                  border: "1px solid var(--border-subtle)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 26,
                  position: "relative",
                  zIndex: 1,
                }}
              >
                {p.icon}
              </div>
              <h3
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  color: "var(--text-primary)",
                  margin: 0,
                  letterSpacing: "-0.01em",
                  position: "relative",
                  zIndex: 1,
                }}
              >
                {p.title}
              </h3>
              <p
                style={{
                  fontSize: 14,
                  color: "var(--text-secondary)",
                  lineHeight: 1.7,
                  margin: 0,
                  position: "relative",
                  zIndex: 1,
                }}
              >
                {p.desc}
              </p>
              {p.href ? (
                <Link
                  href={p.href}
                  className="btn btn-ghost"
                  style={{ marginTop: "auto", alignSelf: "flex-start", fontSize: 13, position: "relative", zIndex: 1 }}
                >
                  {p.cta} →
                </Link>
              ) : (
                <span
                  className="btn btn-ghost"
                  style={{
                    marginTop: "auto",
                    alignSelf: "flex-start",
                    fontSize: 13,
                    opacity: 0.5,
                    cursor: "not-allowed",
                    position: "relative",
                    zIndex: 1,
                  }}
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
