"use client";
import { useEffect, useRef, useState } from "react";
import Vapi from "@vapi-ai/web";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

interface VoiceContext {
  themes: string[];
  booking_code: string;
  variables: {
    top_theme_1: string;
    top_theme_2: string;
    top_theme_3: string;
    themes_joined: string;
    themes_count: string;
    today_date_iso: string;
    today_weekday: string;
    today_human: string;
    next_3_business_days_human: string;
    booking_code: string;
  };
}

interface TranscriptTurn {
  id: string;
  role: "assistant" | "user" | "system";
  text: string;
}

type CallStage = "idle" | "loading_context" | "ready" | "calling" | "ended" | "error";

const VAPI_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY ?? "";
const VAPI_ASSISTANT_ID = process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID ?? "";

let turnCounter = 0;
function turnId() {
  return `turn-${++turnCounter}-${Date.now()}`;
}

export default function VoicePage() {
  const [context, setContext] = useState<VoiceContext | null>(null);
  const [stage, setStage] = useState<CallStage>("loading_context");
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptTurn[]>([]);
  const vapiRef = useRef<Vapi | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const ctx = await api<VoiceContext>("/api/voice/context");
        setContext(ctx);
        setStage("ready");
      } catch (e) {
        setError(`Failed to load voice context: ${e instanceof Error ? e.message : String(e)}`);
        setStage("error");
      }
    })();
  }, []);

  useEffect(() => {
    if (!VAPI_PUBLIC_KEY) return;
    const vapi = new Vapi(VAPI_PUBLIC_KEY);
    vapiRef.current = vapi;

    vapi.on("call-start", () => setStage("calling"));
    vapi.on("call-end", () => setStage("ended"));
    vapi.on("error", (e: unknown) => {
      const msg = e instanceof Error ? e.message : JSON.stringify(e);
      setError(`Vapi error: ${msg}`);
    });
    vapi.on("message", (msg: { type?: string; role?: string; transcript?: string; transcriptType?: string }) => {
      if (msg.type === "transcript" && msg.transcriptType === "final" && msg.transcript) {
        const role: TranscriptTurn["role"] =
          msg.role === "assistant" ? "assistant" : msg.role === "user" ? "user" : "system";
        setTranscript((prev) => [...prev, { id: turnId(), role, text: msg.transcript! }]);
      }
    });

    return () => {
      void vapi.stop();
    };
  }, []);

  async function startCall() {
    if (!vapiRef.current) return;
    if (!VAPI_ASSISTANT_ID) {
      setError("NEXT_PUBLIC_VAPI_ASSISTANT_ID is not set in the frontend env.");
      return;
    }
    setError(null);
    setTranscript([]);
    try {
      // Resolve the signed-in user's UUID; the post-call webhook needs it to
      // look up notification email and attribute the call. Without this,
      // calls.user_id stays null and approve-email fails with "no recipient".
      const { data: { user } } = await createClient().auth.getUser();
      if (!user) {
        setError("You must be signed in to start a call.");
        return;
      }
      // Pull a fresh context per call: each call needs a unique booking_code
      // so the assistant doesn't repeat the same NL-XXXX across calls. Cached
      // page-load context would let a second call reuse the first call's code.
      const ctx = await api<VoiceContext>("/api/voice/context");
      setContext(ctx);
      await vapiRef.current.start(VAPI_ASSISTANT_ID, {
        variableValues: ctx.variables,
        // Echo booking_code in metadata so the post-call webhook persists the
        // same NL-XXXX code the assistant just read out on the call instead
        // of regenerating a different one.
        metadata: { user_id: user.id, booking_code: ctx.booking_code },
      });
    } catch (e) {
      setError(`Failed to start call: ${e instanceof Error ? e.message : String(e)}`);
      setStage("error");
    }
  }

  async function endCall() {
    if (!vapiRef.current) return;
    await vapiRef.current.stop();
  }

  const callable = stage === "ready" || stage === "ended";
  const inCall = stage === "calling";

  return (
    <div style={{ padding: "32px 28px", maxWidth: 920 }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
          🎙️ Voice Agent
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Book a 30-minute advisor consultation. Theme-aware greeting, IST scheduling,
          informational calls only.
        </p>
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

      {!VAPI_PUBLIC_KEY && (
        <div
          className="glass-card"
          style={{ padding: 14, marginBottom: 16, fontSize: 13, color: "var(--text-secondary)" }}
        >
          NEXT_PUBLIC_VAPI_PUBLIC_KEY is not set. Set it in <code>.env.local</code> and restart
          the dev server.
        </div>
      )}

      <ThemesPanel context={context} stage={stage} />

      <div
        className="glass-card"
        style={{
          padding: "16px 18px",
          marginTop: 16,
          display: "flex",
          gap: 12,
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
            {stageLabel(stage)}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
            Greeting → Disclaimer → Topic → Time → 2 slots → Confirm
          </div>
        </div>
        {!inCall ? (
          <button
            onClick={startCall}
            disabled={!callable || !VAPI_PUBLIC_KEY}
            className="btn btn-primary"
          >
            Start call
          </button>
        ) : (
          <button onClick={endCall} className="btn btn-primary">
            End call
          </button>
        )}
      </div>

      {(transcript.length > 0 || inCall) && (
        <div style={{ marginTop: 20 }}>
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
            Live transcript
          </h2>
          <div className="glass-card" style={{ padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
            {transcript.length === 0 ? (
              <div style={{ fontSize: 13, color: "var(--text-muted)", fontStyle: "italic" }}>
                Listening...
              </div>
            ) : (
              transcript.map((t) => <TranscriptRow key={t.id} turn={t} />)
            )}
          </div>
        </div>
      )}

      {stage === "ended" && (
        <div
          className="glass-card"
          style={{
            padding: 14,
            marginTop: 16,
            fontSize: 13,
            color: "var(--text-primary)",
          }}
        >
          Call complete. Your booking has been queued for admin approval. The booking
          code (NL-XXXX) was read to you on the call and will appear in your
          confirmation email once approved.
        </div>
      )}
    </div>
  );
}

function stageLabel(stage: CallStage): string {
  switch (stage) {
    case "loading_context":
      return "Loading current themes...";
    case "ready":
      return "Ready to start the call";
    case "calling":
      return "Call in progress";
    case "ended":
      return "Call ended";
    case "error":
      return "Error";
    default:
      return "";
  }
}

function ThemesPanel({ context, stage }: { context: VoiceContext | null; stage: CallStage }) {
  if (stage === "loading_context") {
    return (
      <div className="glass-card" style={{ padding: 14, fontSize: 13, color: "var(--text-muted)" }}>
        Loading current investor themes...
      </div>
    );
  }
  if (!context || context.themes.length === 0) {
    return (
      <div className="glass-card" style={{ padding: 14, fontSize: 13, color: "var(--text-muted)" }}>
        No pulse generated yet — agent will skip the theme greeting and go straight to the
        disclaimer. Generate a pulse from <code>/admin/pulse</code> for a themed greeting.
      </div>
    );
  }
  return (
    <div className="glass-card" style={{ padding: 14 }}>
      <div
        style={{
          fontSize: 11,
          fontWeight: 700,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: 0.07,
          marginBottom: 8,
        }}
      >
        Current top themes (greeting)
      </div>
      <ol
        style={{
          margin: 0,
          paddingLeft: 18,
          display: "flex",
          flexDirection: "column",
          gap: 4,
          fontSize: 13,
          color: "var(--text-primary)",
        }}
      >
        {context.themes.map((t, i) => (
          <li key={i}>{t}</li>
        ))}
      </ol>
    </div>
  );
}

function TranscriptRow({ turn }: { turn: TranscriptTurn }) {
  const color =
    turn.role === "assistant"
      ? "var(--brand-500, #2f64f8)"
      : turn.role === "user"
        ? "var(--text-primary)"
        : "var(--text-muted)";
  const label = turn.role === "assistant" ? "Agent" : turn.role === "user" ? "You" : "System";
  return (
    <div style={{ fontSize: 13, lineHeight: 1.5 }}>
      <span style={{ fontWeight: 700, color, marginRight: 8 }}>{label}:</span>
      <span style={{ color: "var(--text-secondary)" }}>{turn.text}</span>
    </div>
  );
}
