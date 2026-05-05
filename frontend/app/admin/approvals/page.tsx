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

interface CallDecisionResult {
  call_id: string;
  decision: string;
  results: {
    action_id: string;
    type: PendingAction["type"];
    decision: string;
    execution_status: string | null;
  }[];
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

  async function decideCall(callId: string, status: "approved" | "rejected") {
    setBusy((b) => ({ ...b, [callId]: true }));
    setError(null);
    try {
      const result = await api<CallDecisionResult>(
        `/api/approvals/call/${callId}/decide`,
        { method: "POST", body: JSON.stringify({ status }) },
      );
      // Optimistic: drop every action for this call from the queue
      setItems((prev) => prev.filter((a) => a.call_id !== callId));
      const failed = result.results.filter((r) => r.execution_status === "failed");
      if (failed.length > 0) {
        const types = failed.map((r) => r.type).join(", ");
        setError(
          `Booking approved, but these actions failed at the provider: ${types}. Check action_audit.`,
        );
      }
    } catch (e) {
      setError(`Decision failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy((b) => ({ ...b, [callId]: false }));
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
          <CallHeader
            call={g.call}
            createdAt={g.createdAt}
            actionCount={g.actions.length}
            busy={!!busy[g.callId]}
            onDecide={(status) => decideCall(g.callId, status)}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 12 }}>
            {g.actions.map((a) => (
              <ActionRow key={a.id} action={a} />
            ))}
          </div>
          <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "10px 2px 0" }}>
            One approval fires the calendar hold, sheets row, and Gmail draft together.
          </p>
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

function CallHeader({
  call,
  createdAt,
  actionCount,
  busy,
  onDecide,
}: {
  call: CallSummary | null;
  createdAt: string;
  actionCount: number;
  busy: boolean;
  onDecide: (status: "approved" | "rejected") => void;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        borderBottom: "1px solid var(--border-subtle)",
        paddingBottom: 10,
        flexWrap: "wrap",
      }}
    >
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
            {call?.booking_code ?? "no booking code"}
          </span>
          <span className="badge" style={{ fontSize: 11 }}>
            {actionCount} action{actionCount === 1 ? "" : "s"}
          </span>
          {call?.user_id && (
            <span className="badge" style={{ fontSize: 11 }}>
              user {call.user_id.slice(0, 8)}…
            </span>
          )}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
          Topic: {call?.topic ?? "(general)"} · queued {new Date(createdAt).toLocaleString()}
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
        <button
          onClick={() => onDecide("rejected")}
          disabled={busy}
          className="btn"
          style={{ fontSize: 12 }}
        >
          Reject all
        </button>
        <button
          onClick={() => onDecide("approved")}
          disabled={busy}
          className="btn btn-primary"
          style={{ fontSize: 12 }}
        >
          {busy ? "..." : "Approve all"}
        </button>
      </div>
    </div>
  );
}

function ActionRow({ action }: { action: PendingAction }) {
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
