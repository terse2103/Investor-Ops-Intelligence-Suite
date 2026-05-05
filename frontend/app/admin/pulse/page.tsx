"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Theme {
  name: string;
  review_count: number;
  summary?: string;
}

interface Pulse {
  id?: string;
  generated_at?: string;
  window_start?: string;
  window_end?: string;
  themes: Theme[];
  quotes: string[];
  actions: string[];
  note_text: string;
  word_count?: number;
}

interface ScrapeResult {
  fetched: number;
  accepted: number;
  inserted: number;
  filtered_out: number;
}

const REFRESH_STAGES = {
  idle: "",
  scraping: "Scraping reviews...",
  generating: "Generating pulse...",
  done: "Done",
} as const;

type Stage = keyof typeof REFRESH_STAGES;

export default function PulsePage() {
  const [pulse, setPulse] = useState<Pulse | null>(null);
  const [loading, setLoading] = useState(true);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);
  const [scrapeResult, setScrapeResult] = useState<ScrapeResult | null>(null);

  async function loadLatest() {
    setLoading(true);
    setError(null);
    try {
      const latest = await api<Pulse>("/api/pulse/latest");
      setPulse(latest);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("404")) {
        setPulse(null);
      } else {
        setError("Failed to load latest pulse.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadLatest();
  }, []);

  async function refreshNow() {
    setError(null);
    setScrapeResult(null);
    try {
      setStage("scraping");
      const result = await api<ScrapeResult>("/api/scrape", { method: "POST" });
      setScrapeResult(result);
      setStage("generating");
      const fresh = await api<Pulse>("/api/pulse/generate", { method: "POST" });
      setPulse(fresh);
      setStage("done");
      setTimeout(() => setStage("idle"), 1500);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`Refresh failed: ${msg}`);
      setStage("idle");
    }
  }

  const refreshing = stage !== "idle" && stage !== "done";
  const generated = pulse?.generated_at
    ? new Date(pulse.generated_at).toLocaleString()
    : null;

  return (
    <div style={{ padding: "32px 28px", maxWidth: 920 }}>
      <header
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: 24,
          gap: 16,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: 22,
              fontWeight: 700,
              color: "var(--text-primary)",
              margin: "0 0 4px",
            }}
          >
            Weekly Product Pulse
          </h1>
          <p
            style={{
              fontSize: 13,
              color: "var(--text-secondary)",
              margin: 0,
            }}
          >
            Top 3 themes, 3 verbatim quotes, and 3 action ideas (≤250 words total).
            {generated ? ` Last generated: ${generated}` : ""}
          </p>
        </div>
        <button
          onClick={refreshNow}
          disabled={refreshing}
          className="btn btn-primary"
          style={{ flexShrink: 0 }}
        >
          {refreshing ? REFRESH_STAGES[stage] : "Refresh now"}
        </button>
      </header>

      {error && (
        <div
          className="glass-card"
          style={{
            padding: 14,
            marginBottom: 16,
            borderColor: "var(--danger, #c33)",
            color: "var(--danger, #c33)",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      {scrapeResult && stage === "generating" && (
        <div
          className="glass-card"
          style={{ padding: 12, marginBottom: 16, fontSize: 12 }}
        >
          Scraped: {scrapeResult.fetched} fetched, {scrapeResult.accepted}{" "}
          accepted, {scrapeResult.inserted} new.
        </div>
      )}

      {loading && !pulse && (
        <div className="glass-card" style={{ padding: 40, textAlign: "center" }}>
          Loading pulse...
        </div>
      )}

      {!loading && !pulse && !error && (
        <div className="glass-card" style={{ padding: 40, textAlign: "center" }}>
          <h2
            style={{
              fontSize: 16,
              fontWeight: 700,
              margin: "0 0 8px",
              color: "var(--text-primary)",
            }}
          >
            No pulse yet
          </h2>
          <p
            style={{
              fontSize: 13,
              color: "var(--text-secondary)",
              margin: 0,
            }}
          >
            Click &ldquo;Refresh now&rdquo; to scrape reviews and generate the
            first pulse.
          </p>
        </div>
      )}

      {pulse && (
        <>
          <Section title="Top 3 themes">
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr",
                gap: 10,
              }}
            >
              {pulse.themes.map((t, i) => (
                <div
                  key={i}
                  className="glass-card"
                  style={{ padding: "14px 16px" }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 4,
                    }}
                  >
                    <span
                      style={{
                        fontSize: 14,
                        fontWeight: 700,
                        color: "var(--text-primary)",
                      }}
                    >
                      {i + 1}. {t.name}
                    </span>
                    <span
                      className="badge"
                      style={{ fontSize: 11 }}
                    >
                      {t.review_count} reviews
                    </span>
                  </div>
                  {t.summary && (
                    <div
                      style={{
                        fontSize: 12,
                        color: "var(--text-muted)",
                        lineHeight: 1.5,
                      }}
                    >
                      {t.summary}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Section>

          <Section title="Verbatim quotes">
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {pulse.quotes.map((q, i) => (
                <blockquote
                  key={i}
                  className="glass-card"
                  style={{
                    padding: "12px 16px",
                    margin: 0,
                    fontStyle: "italic",
                    fontSize: 13,
                    color: "var(--text-secondary)",
                    borderLeft: "3px solid var(--accent, #6c5ce7)",
                  }}
                >
                  &ldquo;{q}&rdquo;
                </blockquote>
              ))}
            </div>
          </Section>

          <Section title="Action ideas">
            <ul
              style={{
                margin: 0,
                paddingLeft: 20,
                listStyleType: "disc",
                display: "flex",
                flexDirection: "column",
                gap: 8,
                fontSize: 13,
                color: "var(--text-primary)",
              }}
            >
              {pulse.actions.map((a, i) => (
                <li key={i} style={{ lineHeight: 1.5 }}>
                  {a}
                </li>
              ))}
            </ul>
          </Section>
        </>
      )}
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section style={{ marginBottom: 20 }}>
      <h2
        style={{
          fontSize: 13,
          fontWeight: 700,
          color: "var(--text-secondary)",
          textTransform: "uppercase",
          letterSpacing: 0.5,
          margin: "0 0 8px",
        }}
      >
        {title}
      </h2>
      {children}
    </section>
  );
}
