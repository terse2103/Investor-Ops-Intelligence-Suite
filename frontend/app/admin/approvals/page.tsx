"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface CallSummary {
  id: string;
  user_id: string | null;
  booking_code: string | null;
  topic: string | null;
  started_at: string | null;
}

interface PendingAction {
  id: string;
  call_id: string;
  type: "calendar" | "sheets" | "email";
  status: string;
  payload: Record<string, unknown>;
  created_at: string;
  calls?: CallSummary | null;
}

interface DecisionResult {
  action_id: string;
  decision: string;
  execution_status: string | null;
  notification: { status: string } | null;
}

const TYPE_META: Record<PendingAction["type"], { icon: string; label: string }> = {
  calendar: { icon: "📅", label: "Calendar hold" },
  sheets: { icon: "📋", label: "Sheets row" },
  email: { icon: "📧", label: "Gmail draft" },
};

export default function ApprovalsPage() {
  const [items, setItems] = useState<PendingAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<Record<string, boolean>>({});

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const resp = await api<{ items: PendingAction[] }>("/api/approvals/pending");
      setItems(resp.items);
    } catch (e) {
      setError(`Failed to load pending actions: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, []);

  async function decide(action: PendingAction, status: "approved" | "rejected") {
    setBusy((b) => ({ ...b, [action.id]: true }));
    setError(null);
    try {
      const result = await api<DecisionResult>(
        `/api/approvals/${action.id}/decide`,
        { method: "POST", body: JSON.stringify({ status }) },
      );
      // Optimistic: drop the action from the queue
      setItems((prev) => prev.filter((a) => a.id !== action.id));
      if (result.execution_status === "failed") {
        setError(
          `Action ${action.type} executed but the provider reported a failure. Check action_audit.`,
        );
      }
    } catch (e) {
      setError(`Decision failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy((b) => ({ ...b, [action.id]: false }));
    }
  }

  // Group actions by call_id for the per-booking layout
  const groups = groupByCall(items);

  return (
    <div style={{ padding: "32px 28px", maxWidth: 920 }}>
      <header
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          marginBottom: 20,
        }}
      >
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
            Approval Center
          </h1>
          <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
            HITL gate for post-call Calendar holds, Sheets rows, and Gmail drafts.
            No external action fires without your approval.
          </p>
        </div>
        <button onClick={load} className="btn btn-primary" disabled={loading}>
          {loading ? "Loading..." : "Refresh"}
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

      {!loading && groups.length === 0 && (
        <div className="glass-card" style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>
          <div style={{ fontSize: 36, marginBottom: 8 }}>✅</div>
          <div style={{ fontSize: 14 }}>No pending approvals.</div>
        </div>
      )}

      {groups.map((g) => (
        <div key={g.callId} className="glass-card" style={{ padding: 16, marginBottom: 14 }}>
          <CallHeader call={g.call} createdAt={g.createdAt} />
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
            {g.actions.map((a) => (
              <ActionRow
                key={a.id}
                action={a}
                busy={!!busy[a.id]}
                onDecide={decide}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function groupByCall(items: PendingAction[]): {
  callId: string;
  call: CallSummary | null;
  actions: PendingAction[];
  createdAt: string;
}[] {
  const map = new Map<string, { call: CallSummary | null; actions: PendingAction[]; createdAt: string }>();
  for (const a of items) {
    const key = a.call_id;
    const existing = map.get(key);
    if (existing) {
      existing.actions.push(a);
    } else {
      map.set(key, { call: a.calls ?? null, actions: [a], createdAt: a.created_at });
    }
  }
  return Array.from(map.entries())
    .sort(([, a], [, b]) => (a.createdAt < b.createdAt ? 1 : -1))
    .map(([callId, v]) => ({ callId, ...v }));
}

function CallHeader({ call, createdAt }: { call: CallSummary | null; createdAt: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        borderBottom: "1px solid var(--border-subtle)",
        paddingBottom: 8,
      }}
    >
      <div>
        <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
          {call?.booking_code ?? "no booking code"}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
          Topic: {call?.topic ?? "(general)"} · queued {new Date(createdAt).toLocaleString()}
        </div>
      </div>
      {call?.user_id && (
        <span className="badge" style={{ fontSize: 11 }}>
          user {call.user_id.slice(0, 8)}…
        </span>
      )}
    </div>
  );
}

function ActionRow({
  action,
  busy,
  onDecide,
}: {
  action: PendingAction;
  busy: boolean;
  onDecide: (action: PendingAction, status: "approved" | "rejected") => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const meta = TYPE_META[action.type];
  return (
    <div
      style={{
        background: "var(--bg-muted)",
        borderRadius: 10,
        padding: "10px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 18 }}>{meta.icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
            {meta.label}
          </div>
          <button
            onClick={() => setOpen((o) => !o)}
            style={{
              background: "transparent",
              border: "none",
              padding: 0,
              fontSize: 11,
              color: "var(--text-muted)",
              cursor: "pointer",
              textAlign: "left",
            }}
          >
            {open ? "▾ hide payload" : "▸ show payload"}
          </button>
        </div>
        <button
          onClick={() => onDecide(action, "rejected")}
          disabled={busy}
          className="btn"
          style={{ fontSize: 12 }}
        >
          Reject
        </button>
        <button
          onClick={() => onDecide(action, "approved")}
          disabled={busy}
          className="btn btn-primary"
          style={{ fontSize: 12 }}
        >
          {busy ? "..." : "Approve"}
        </button>
      </div>
      {open && (
        <pre
          style={{
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: 8,
            padding: 10,
            fontSize: 11,
            margin: 0,
            overflow: "auto",
            maxHeight: 220,
            color: "var(--text-secondary)",
          }}
        >
          {JSON.stringify(action.payload, null, 2)}
        </pre>
      )}
    </div>
  );
}
