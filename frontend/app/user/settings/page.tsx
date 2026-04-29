"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Contact {
  email: string | null;
  updated_at: string | null;
}

export default function SettingsPage() {
  const [email, setEmail] = useState("");
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const ctx = await api<Contact>("/api/settings/contact");
        if (ctx.email) setEmail(ctx.email);
        setSavedAt(ctx.updated_at);
      } catch (e) {
        setError(`Failed to load contact: ${e instanceof Error ? e.message : String(e)}`);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSaving(true);
    try {
      const result = await api<Contact>("/api/settings/contact", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setSavedAt(result.updated_at);
      setSuccess("Saved.");
    } catch (e) {
      setError(`Save failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ padding: "32px 28px", maxWidth: 620 }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, color: "var(--text-primary)", margin: "0 0 4px" }}>
          Settings
        </h1>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          Notification email used when an admin approves or rejects your booking. We send
          one email per booking decision (R-APPROVE4).
        </p>
      </header>

      <form onSubmit={save} className="glass-card" style={{ padding: 20 }}>
        <label
          htmlFor="email-input"
          style={{
            display: "block",
            fontSize: 12,
            fontWeight: 700,
            color: "var(--text-muted)",
            textTransform: "uppercase",
            letterSpacing: 0.07,
            marginBottom: 6,
          }}
        >
          Notification email
        </label>
        <input
          id="email-input"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          disabled={loading}
          style={{
            width: "100%",
            padding: "10px 14px",
            borderRadius: 10,
            border: "1px solid var(--border-subtle)",
            background: "var(--bg-surface)",
            color: "var(--text-primary)",
            fontSize: 14,
            fontFamily: "Inter, sans-serif",
          }}
        />

        {savedAt && (
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 6 }}>
            Last saved: {new Date(savedAt).toLocaleString()}
          </div>
        )}

        {error && (
          <div style={{ marginTop: 12, padding: 10, borderRadius: 8, background: "rgba(204,51,51,0.08)", color: "var(--danger, #c33)", fontSize: 12 }}>
            {error}
          </div>
        )}
        {success && (
          <div style={{ marginTop: 12, padding: 10, borderRadius: 8, background: "rgba(34,197,94,0.08)", color: "var(--success, #1a8c4a)", fontSize: 12 }}>
            {success}
          </div>
        )}

        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading || saving}
          style={{ marginTop: 16 }}
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </form>
    </div>
  );
}
