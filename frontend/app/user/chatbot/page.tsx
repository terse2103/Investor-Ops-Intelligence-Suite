"use client";
import { useState, useRef, useEffect } from "react";
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
  "This chatbot provides factual information only. It cannot give investment advice, compare schemes, or predict returns. Every answer is sourced directly from the INDMoney corpus.";

const SUGGESTIONS = [
  "What is the expense ratio of Nippon India ELSS Tax Saver Fund?",
  "What is the lock-in period of Nippon India ELSS Tax Saver Fund?",
  "Tell me about Nippon India Silver ETF Fund of Fund.",
  "What is Nippon India Balanced Advantage Fund about?",
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
          alignItems: "center",
          justifyContent: "space-between",
          background: "var(--bg-surface)",
        }}
      >
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
            🧠 RAG Chatbot
          </h1>
          <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "2px 0 0" }}>
            Facts-only Q&amp;A · Nippon India mutual fund corpus
          </p>
        </div>
        <span className="badge badge-brand">Pillar A — Smart-Sync KB</span>
      </header>

      {/* Disclaimer banner */}
      <div
        style={{
          flexShrink: 0,
          margin: "0 28px",
          marginTop: 16,
          padding: "10px 16px",
          borderRadius: 10,
          background: "rgba(234, 179, 8, 0.08)",
          border: "1px solid rgba(234, 179, 8, 0.2)",
          display: "flex",
          gap: 10,
          alignItems: "flex-start",
        }}
        role="note"
        aria-label="Disclaimer"
      >
        <span style={{ fontSize: 14, flexShrink: 0 }}>⚠️</span>
        <p style={{ fontSize: 12, color: "#f6d860", margin: 0, lineHeight: 1.5 }}>
          {DISCLAIMER}
        </p>
      </div>

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
      style={{ display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center", paddingTop: 40 }}
    >
      <div style={{ fontSize: 56, marginBottom: 16 }}>🧠</div>
      <h2 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 8px" }}>
        Smart-Sync Knowledge Base
      </h2>
      <p style={{ fontSize: 14, color: "var(--text-secondary)", maxWidth: 400, lineHeight: 1.6, marginBottom: 32 }}>
        Ask any question about Nippon India mutual fund schemes. Every answer is
        cited directly from the INDMoney corpus — no investment advice, ever.
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, width: "100%", maxWidth: 520 }}>
        <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 4 }}>
          Try a question
        </p>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSuggestion(s)}
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
              borderRadius: 10,
              padding: "10px 16px",
              textAlign: "left",
              cursor: "pointer",
              color: "var(--text-secondary)",
              fontSize: 13,
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
            border: `1px solid ${
              msg.error
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
              <div>
                <span style={{ fontWeight: 700, color: "var(--text-secondary)" }}>Source: </span>
                {msg.citations.map((url) => (
                  <a
                    key={url}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: "var(--brand-400)", textDecoration: "underline", overflowWrap: "break-word" }}
                  >
                    {url}
                  </a>
                ))}
              </div>
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

function FormattedAnswer({ text, isRefusal }: { text: string; isRefusal: boolean }) {
  if (isRefusal) {
    return (
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
        <span style={{ fontSize: 16, flexShrink: 0 }}>🚫</span>
        <span style={{ color: "#f6d860", fontStyle: "italic" }}>{text}</span>
      </div>
    );
  }

  // Render bullet lists nicely
  const parts = text.split("\n").filter(Boolean);
  if (parts.length > 1 && parts.some((p) => p.startsWith("•") || p.startsWith("-") || p.startsWith("*"))) {
    return (
      <ul style={{ margin: 0, padding: "0 0 0 20px", display: "flex", flexDirection: "column", gap: 4 }}>
        {parts.map((part, i) => (
          <li key={i} style={{ color: "var(--text-primary)" }}>
            {part.replace(/^[•\-\*]\s*/, "")}
          </li>
        ))}
      </ul>
    );
  }

  return <>{text}</>;
}
