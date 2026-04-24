// Shared sidebar shell for all /admin/* pages.
"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

const NAV_ITEMS = [
  { href: "/admin/pulse",     label: "Weekly Pulse",    icon: "📊" },
  { href: "/admin/approvals", label: "Approval Center", icon: "✅" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();

  async function signOut() {
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg-base)" }}>
      {/* Sidebar */}
      <aside
        style={{
          width: 230,
          flexShrink: 0,
          borderRight: "1px solid var(--border-subtle)",
          display: "flex",
          flexDirection: "column",
          padding: "20px 12px",
          background: "var(--bg-surface)",
          position: "sticky",
          top: 0,
          height: "100vh",
          overflowY: "auto",
        }}
      >
        {/* Logo + admin badge */}
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "4px 10px 16px",
            textDecoration: "none",
            borderBottom: "1px solid var(--border-subtle)",
            marginBottom: 12,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: "linear-gradient(135deg, #7c3aed, #a78bfa)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              fontWeight: 800,
              color: "#fff",
              flexShrink: 0,
              boxShadow: "0 2px 10px rgba(124,58,237,0.35)",
            }}
          >
            IO
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 12, color: "var(--text-primary)", lineHeight: 1 }}>
              Investor Ops
            </div>
            <div style={{ fontSize: 10, color: "#a78bfa", fontWeight: 600 }}>ADMIN</div>
          </div>
        </Link>

        <nav style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
          <p style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", padding: "4px 14px", marginBottom: 4 }}>
            Admin
          </p>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-link ${pathname === item.href ? "active" : ""}`}
              style={{ borderRight: pathname === item.href ? "2px solid #a78bfa" : undefined } as React.CSSProperties}
            >
              <span style={{ fontSize: 16 }}>{item.icon}</span>
              {item.label}
            </Link>
          ))}
          <div style={{ borderTop: "1px solid var(--border-subtle)", marginTop: 8, paddingTop: 8 }}>
            <p style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", padding: "4px 14px", marginBottom: 4 }}>
              User area
            </p>
            <Link href="/user/chatbot" className="nav-link">
              <span style={{ fontSize: 16 }}>🧠</span>
              RAG Chatbot
            </Link>
          </div>
        </nav>

        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 12, marginTop: 12 }}>
          <button
            id="admin-signout"
            onClick={signOut}
            className="nav-link"
            style={{ width: "100%", background: "none", border: "none", cursor: "pointer", textAlign: "left" }}
          >
            <span style={{ fontSize: 16 }}>🚪</span>
            Sign out
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, overflow: "auto" }}>{children}</main>
    </div>
  );
}
