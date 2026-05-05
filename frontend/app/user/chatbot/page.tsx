"use client";
import { useState, useRef, useEffect } from "react";
import type { ReactNode } from "react";
import { api } from "@/lib/api";

// --- Types ---
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: string[];
  lastUpdated?: string | null;
  error?: boolean;
}

interface RagResponse {
  answer: string;
  citations: string[];
  last_updated: string | null;
}

// --- Helpers ---
let msgCounter = 0;
function uid() {
  return `msg-${++msgCounter}-${Date.now()}`;
}

const DISCLAIMER =
  "This chatbot provides factual information only. It cannot give investment advice, compare schemes, or predict returns.";

const MF_SCHEMES = [
  "Nippon India ELSS Tax Saver Fund",
  "Nippon India Nifty Auto Index Fund",
  "Nippon India Short Duration Fund",
  "Nippon India CRISIL IBX AAA Fin Svcs Dec 2026 Index Fund",
  "Nippon India Silver ETF Fund of Fund",
  "Nippon India Balanced Advantage Fund",
];

const FEE_SCENARIOS = [
  "Expense Ratio",
  "Assets Under Management (AUM)",
  "Exit Load",
  "Net Asset Value (NAV)",
];

const SUGGESTIONS = [
  "What is the expense ratio of Nippon India ELSS Tax Saver Fund?",
  "What is the lock-in period of Nippon India ELSS Tax Saver Fund?",
  "What is exit load and how does it work?",
  "What is the exit load on Nippon India Short Duration Fund and what does exit load mean?",
];

export default function ChatbotPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage(question: string) {
    const q = question.trim();
    if (!q || loading) return;

    const userMsg: Message = { id: uid(), role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const data = await api<RagResponse>("/api/rag/query", {
        method: "POST",
        body: JSON.stringify({ question: q }),
      });

      const assistantMsg: Message = {
        id: uid(),
        role: "assistant",
        content: data.answer,
        citations: data.citations,
        lastUpdated: data.last_updated,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errMsg: Message = {
        id: uid(),
        role: "assistant",
        content:
          "Something went wrong connecting to the knowledge base. Please try again.",
        error: true,
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  const isEmpty = messages.length === 0;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <header
        style={{
          flexShrink: 0,
          padding: "18px 28px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
          background: "var(--bg-surface)",
        }}
      >
        <div style={{ minWidth: 0, flex: 1 }}>
          <h1 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            🧠 RAG Chatbot
          </h1>
          <p
            role="note"
            aria-label="Disclaimer"
            style={{ fontSize: 12, color: "var(--text-secondary)", margin: "4px 0 0", lineHeight: 1.5, maxWidth: 760 }}
          >
            {DISCLAIMER}
          </p>
        </div>
        <span className="badge badge-brand" style={{ flexShrink: 0 }}>Smart-Sync KB</span>
      </header>

      {/* Messages area */}
      <div
        id="chat-messages"
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "24px 28px",
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        {isEmpty ? (
          <EmptyState onSuggestion={sendMessage} />
        ) : (
          messages.map((msg) =>
            msg.role === "user" ? (
              <UserBubble key={msg.id} content={msg.content} />
            ) : (
              <AssistantBubble key={msg.id} msg={msg} />
            ),
          )
        )}

        {/* Typing indicator */}
        {loading && (
          <div className="fade-up" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: "linear-gradient(135deg, #2f64f8, #578dff)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
                flexShrink: 0,
              }}
            >
              🧠
            </div>
            <div
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "0 14px 14px 14px",
                padding: "14px 18px",
                display: "flex",
                gap: 5,
                alignItems: "center",
              }}
            >
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Input area */}
      <div
        style={{
          flexShrink: 0,
          padding: "16px 28px 24px",
          borderTop: "1px solid var(--border-subtle)",
          background: "var(--bg-surface)",
        }}
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendMessage(input);
          }}
          style={{ display: "flex", gap: 10, alignItems: "flex-end" }}
        >
          <textarea
            id="chat-input"
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask a question about Nippon India mutual funds…"
            disabled={loading}
            rows={1}
            style={{
              flex: 1,
              background: "var(--bg-muted)",
              border: "1px solid var(--border-default)",
              borderRadius: 12,
              color: "var(--text-primary)",
              fontFamily: "Inter, sans-serif",
              fontSize: 14,
              padding: "12px 16px",
              resize: "none",
              maxHeight: 120,
              overflowY: "auto",
              transition: "border-color 0.18s, box-shadow 0.18s",
              lineHeight: 1.5,
            }}
            onFocus={(e) => {
              e.target.style.borderColor = "var(--brand-500)";
              e.target.style.boxShadow = "0 0 0 3px rgba(47,100,248,0.15)";
            }}
            onBlur={(e) => {
              e.target.style.borderColor = "var(--border-default)";
              e.target.style.boxShadow = "none";
            }}
          />
          <button
            id="chat-send"
            type="submit"
            disabled={loading || !input.trim()}
            className="btn btn-primary"
            style={{ padding: "12px 20px", flexShrink: 0, borderRadius: 12 }}
            aria-label="Send message"
          >
            {loading ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" style={{ animation: "spin 0.8s linear infinite" }}>
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeDasharray="31.416" strokeDashoffset="10" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            )}
          </button>
        </form>
        <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 8, textAlign: "center" }}>
          Enter to send · Shift+Enter for newline · Answers are sourced from the INDMoney corpus
        </p>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

// --- Sub-components ---

function EmptyState({ onSuggestion }: { onSuggestion: (q: string) => void }) {
  return (
    <div
      className="fade-up"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        paddingTop: 64,
        paddingBottom: 48,
        gap: 36,
        maxWidth: 640,
        margin: "0 auto",
        width: "100%",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 18 }}>
        <div
          style={{
            width: 88,
            height: 88,
            borderRadius: 22,
            background: "linear-gradient(135deg, rgba(47,100,248,0.20), rgba(167,139,250,0.18))",
            border: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 44,
            boxShadow: "0 12px 32px -16px rgba(47,100,248,0.45)",
          }}
        >
          🧠
        </div>
        <h2 style={{ fontSize: 26, fontWeight: 700, color: "var(--text-primary)", margin: 0, letterSpacing: "-0.01em" }}>
          Smart-Sync Knowledge Base
        </h2>
        <p style={{ fontSize: 15, color: "var(--text-secondary)", maxWidth: 520, lineHeight: 1.7, margin: 0 }}>
          Ask factual questions about specific Nippon India mutual fund schemes
          or general fee/metric concepts. Every answer is cited from the indexed
          corpus, no investment advice, ever.
        </p>
      </div>

      <CoverageCard />

      <div style={{ display: "flex", flexDirection: "column", gap: 14, width: "100%", maxWidth: 560 }}>
        <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em", margin: 0 }}>
          Try a question
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onSuggestion(s)}
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: 12,
                padding: "12px 18px",
                textAlign: "left",
                cursor: "pointer",
                color: "var(--text-secondary)",
                fontSize: 13,
                lineHeight: 1.5,
                transition: "all 0.15s",
                fontFamily: "Inter, sans-serif",
              }}
              onMouseEnter={(e) => {
                (e.target as HTMLButtonElement).style.background = "var(--bg-elevated)";
                (e.target as HTMLButtonElement).style.color = "var(--text-primary)";
                (e.target as HTMLButtonElement).style.borderColor = "var(--brand-500)";
              }}
              onMouseLeave={(e) => {
                (e.target as HTMLButtonElement).style.background = "var(--bg-surface)";
                (e.target as HTMLButtonElement).style.color = "var(--text-secondary)";
                (e.target as HTMLButtonElement).style.borderColor = "var(--border-subtle)";
              }}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function CoverageCard() {
  return (
    <div
      className="glass-card"
      style={{
        width: "100%",
        maxWidth: 560,
        padding: 22,
        textAlign: "left",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        aria-hidden
        style={{
          position: "absolute",
          top: -50,
          right: -50,
          width: 180,
          height: 180,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(47,100,248,0.18) 0%, transparent 70%)",
          pointerEvents: "none",
        }}
      />
      <p
        style={{
          fontSize: 11,
          fontWeight: 700,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          margin: "0 0 14px",
          position: "relative",
        }}
      >
        What this corpus covers
      </p>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 18,
          position: "relative",
        }}
      >
        <CoverageColumn
          icon="📈"
          title="MF schemes"
          accent="rgba(47,100,248,0.18)"
          items={MF_SCHEMES}
        />
        <CoverageColumn
          icon="💰"
          title="Fee scenarios"
          accent="rgba(167,139,250,0.20)"
          items={FEE_SCENARIOS}
        />
      </div>
    </div>
  );
}

function CoverageColumn({
  icon,
  title,
  accent,
  items,
}: {
  icon: string;
  title: string;
  accent: string;
  items: string[];
}) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
        <span
          style={{
            width: 26,
            height: 26,
            borderRadius: 7,
            background: accent,
            border: "1px solid var(--border-subtle)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 14,
            flexShrink: 0,
          }}
        >
          {icon}
        </span>
        <span
          style={{
            fontSize: 12,
            fontWeight: 700,
            color: "var(--text-primary)",
            letterSpacing: "0.02em",
          }}
        >
          {title}
        </span>
      </div>
      <ul
        style={{
          margin: 0,
          padding: 0,
          listStyle: "none",
          display: "flex",
          flexDirection: "column",
          gap: 6,
        }}
      >
        {items.map((item) => (
          <li
            key={item}
            style={{
              fontSize: 12.5,
              color: "var(--text-secondary)",
              lineHeight: 1.5,
              paddingLeft: 10,
              position: "relative",
            }}
          >
            <span
              aria-hidden
              style={{
                position: "absolute",
                left: 0,
                top: 8,
                width: 4,
                height: 4,
                borderRadius: "50%",
                background: "var(--text-muted)",
              }}
            />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function UserBubble({ content }: { content: string }) {
  return (
    <div
      className="fade-up"
      style={{ display: "flex", justifyContent: "flex-end", gap: 12 }}
    >
      <div
        style={{
          maxWidth: "70%",
          background: "linear-gradient(135deg, var(--brand-600), var(--brand-500))",
          borderRadius: "14px 14px 4px 14px",
          padding: "12px 18px",
          fontSize: 14,
          color: "#fff",
          lineHeight: 1.6,
          boxShadow: "0 2px 12px rgba(47,100,248,0.3)",
        }}
      >
        {content}
      </div>
    </div>
  );
}

function AssistantBubble({ msg }: { msg: Message }) {
  // Parse out citation lines from the answer body for cleaner display
  const lines = msg.content.split("\n");
  const sourceLineIdx = lines.findIndex((l) => l.startsWith("Source:"));
  const updatedLineIdx = lines.findIndex((l) => l.startsWith("Last updated"));

  const bodyLines = lines.filter(
    (_, i) => i !== sourceLineIdx && i !== updatedLineIdx,
  );
  const bodyText = bodyLines.join("\n").trim();

  // Detect refusal messages
  const isRefusal =
    msg.content.includes("I can't give investment advice") ||
    msg.content.includes("I can't compare schemes") ||
    msg.content.includes("I don't have a verified source");

  return (
    <div className="fade-up" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
      {/* Avatar */}
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: "50%",
          background: msg.error
            ? "rgba(239,68,68,0.2)"
            : "linear-gradient(135deg, #2f64f8, #578dff)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 14,
          flexShrink: 0,
          border: msg.error ? "1px solid rgba(239,68,68,0.3)" : "none",
        }}
      >
        {msg.error ? "⚠️" : "🧠"}
      </div>

      {/* Bubble */}
      <div style={{ maxWidth: "75%", display: "flex", flexDirection: "column", gap: 8 }}>
        <div
          style={{
            background: msg.error
              ? "rgba(239,68,68,0.07)"
              : isRefusal
                ? "rgba(234,179,8,0.07)"
                : "var(--bg-surface)",
            border: `1px solid ${msg.error
                ? "rgba(239,68,68,0.2)"
                : isRefusal
                  ? "rgba(234,179,8,0.2)"
                  : "var(--border-subtle)"
              }`,
            borderRadius: "0 14px 14px 14px",
            padding: "14px 18px",
            fontSize: 14,
            color: msg.error ? "#f87171" : "var(--text-primary)",
            lineHeight: 1.7,
          }}
        >
          <FormattedAnswer text={bodyText} isRefusal={isRefusal} />
        </div>

        {/* Citations & timestamp */}
        {!msg.error && (msg.citations?.length || msg.lastUpdated) && (
          <div
            style={{
              padding: "8px 12px",
              background: "var(--bg-elevated)",
              borderRadius: 8,
              fontSize: 11,
              color: "var(--text-muted)",
              display: "flex",
              flexDirection: "column",
              gap: 4,
            }}
          >
            {msg.citations && msg.citations.length > 0 && (
              msg.citations.length === 1 ? (
                <div>
                  <span style={{ fontWeight: 700, color: "var(--text-secondary)" }}>Source: </span>
                  <a
                    href={msg.citations[0]}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "var(--brand-400)", textDecoration: "underline", overflowWrap: "break-word" }}
                  >
                    {msg.citations[0]}
                  </a>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <span style={{ fontWeight: 700, color: "var(--text-secondary)" }}>
                    Sources ({msg.citations.length}):
                  </span>
                  {msg.citations.map((url, idx) => (
                    <div
                      key={url}
                      style={{
                        display: "flex",
                        gap: 8,
                        alignItems: "flex-start",
                        paddingLeft: 4,
                      }}
                    >
                      <span
                        style={{
                          color: "var(--text-secondary)",
                          fontWeight: 700,
                          flexShrink: 0,
                          minWidth: 16,
                        }}
                      >
                        {idx + 1}.
                      </span>
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          color: "var(--brand-400)",
                          textDecoration: "underline",
                          overflowWrap: "anywhere",
                          wordBreak: "break-all",
                        }}
                      >
                        {url}
                      </a>
                    </div>
                  ))}
                </div>
              )
            )}
            {msg.lastUpdated && (
              <div>
                <span style={{ fontWeight: 700, color: "var(--text-secondary)" }}>Last updated from sources: </span>
                {msg.lastUpdated}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Renders **bold** spans (Markdown's only formatting the LLM is asked to emit).
// Anything else is left as plain text so the body never displays raw `**`.
function renderInline(text: string, keyPrefix = "i"): ReactNode[] {
  const nodes: ReactNode[] = [];
  const re = /\*\*([^*]+)\*\*/g;
  let cursor = 0;
  let match: RegExpExecArray | null;
  let n = 0;
  while ((match = re.exec(text)) !== null) {
    if (match.index > cursor) {
      nodes.push(text.slice(cursor, match.index));
    }
    nodes.push(<strong key={`${keyPrefix}-${n++}`}>{match[1]}</strong>);
    cursor = match.index + match[0].length;
  }
  if (cursor < text.length) nodes.push(text.slice(cursor));
  return nodes;
}

type AnswerBlock =
  | { type: "bullet"; content: string }
  | { type: "para"; content: string };

// Group raw answer lines into bullets and paragraphs. A bullet starts on a
// line that begins with `-`, `*`, or `•`; subsequent non-bullet lines are
// folded back into the previous bullet so multi-line bullets don't get
// shredded into adjacent <li>s (the original bug: continuation lines became
// their own bullets, making it impossible to tell where a point ended).
function parseAnswer(text: string): AnswerBlock[] {
  const lines = text.split("\n");
  const blocks: AnswerBlock[] = [];
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (!line.trim()) continue;
    const bullet = line.match(/^\s*[-•*]\s+(.*)$/);
    if (bullet) {
      blocks.push({ type: "bullet", content: bullet[1].trim() });
      continue;
    }
    const last = blocks[blocks.length - 1];
    if (last && last.type === "bullet") {
      last.content += " " + line.trim();
    } else {
      blocks.push({ type: "para", content: line.trim() });
    }
  }
  return blocks;
}

function FormattedAnswer({ text, isRefusal }: { text: string; isRefusal: boolean }) {
  if (isRefusal) {
    return (
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
        <span style={{ fontSize: 16, flexShrink: 0 }}>🚫</span>
        <span style={{ color: "#f6d860", fontStyle: "italic" }}>{text}</span>
      </div>
    );
  }

  const blocks = parseAnswer(text);
  const hasBullets = blocks.some((b) => b.type === "bullet");

  // Mixed content (bullets + paragraphs): render paragraphs as standalone <p>
  // and group consecutive bullets into a single <ul>. Tailwind 4 Preflight
  // resets list-style to none, so we set listStyleType explicitly.
  if (hasBullets) {
    const out: ReactNode[] = [];
    let buffer: AnswerBlock[] = [];
    const flushBullets = () => {
      if (buffer.length === 0) return;
      out.push(
        <ul
          key={`ul-${out.length}`}
          style={{
            margin: 0,
            padding: "0 0 0 22px",
            listStyleType: "disc",
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          {buffer.map((b, i) => (
            <li
              key={i}
              style={{ color: "var(--text-primary)", lineHeight: 1.65, paddingLeft: 4 }}
            >
              {renderInline(b.content, `b${out.length}-${i}`)}
            </li>
          ))}
        </ul>,
      );
      buffer = [];
    };
    blocks.forEach((b, i) => {
      if (b.type === "bullet") {
        buffer.push(b);
      } else {
        flushBullets();
        out.push(
          <p key={`p-${i}`} style={{ margin: out.length === 0 ? 0 : "8px 0 0" }}>
            {renderInline(b.content, `p${i}`)}
          </p>,
        );
      }
    });
    flushBullets();
    return <>{out}</>;
  }

  // No bullets: render each line as its own paragraph so the visual line
  // breaks the model emitted are preserved (otherwise React collapses \n).
  return (
    <>
      {blocks.map((b, i) => (
        <p key={i} style={{ margin: i === 0 ? 0 : "8px 0 0" }}>
          {renderInline(b.content, `t${i}`)}
        </p>
      ))}
    </>
  );
}
