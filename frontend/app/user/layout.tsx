// Shared sidebar shell for all /user/* pages.
"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

const NAV_ITEMS = [
  { href: "/user/chatbot", label: "RAG Chatbot", icon: "🧠" },
  { href: "/user/voice",   label: "Voice Agent",  icon: "🎙️" },
  { href: "/user/settings", label: "Settings",   icon: "⚙️" },
];

const COLLAPSE_STORAGE_KEY = "user-sidebar-collapsed";

export default function UserLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const supabase = createClient();
  const [collapsed, setCollapsed] = useState(false);

  // Hydrate collapse preference from localStorage after mount to avoid SSR mismatch.
  useEffect(() => {
    if (typeof window === "undefined") return;
    setCollapsed(window.localStorage.getItem(COLLAPSE_STORAGE_KEY) === "1");
  }, []);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== "undefined") {
        window.localStorage.setItem(COLLAPSE_STORAGE_KEY, next ? "1" : "0");
      }
      return next;
    });
  }

  async function signOut() {
    await supabase.auth.signOut();
    router.push("/login");
  }

  const sidebarWidth = collapsed ? 72 : 230;

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        background: "var(--bg-base)",
      }}
    >
      {/* Sidebar */}
      <aside
        style={{
          width: sidebarWidth,
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
          overflowX: "hidden",
          transition: "width 180ms ease",
        }}
      >
        {/* Logo + collapse toggle */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: collapsed ? "center" : "space-between",
            gap: 8,
            padding: "4px 4px 16px",
            borderBottom: "1px solid var(--border-subtle)",
            marginBottom: 12,
          }}
        >
          <Link
            href="/"
            title={collapsed ? "Investor Ops" : undefined}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              textDecoration: "none",
              flex: collapsed ? "0 0 auto" : 1,
              minWidth: 0,
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "linear-gradient(135deg, #2f64f8, #578dff)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 14,
                fontWeight: 800,
                color: "#fff",
                flexShrink: 0,
                boxShadow: "0 2px 10px rgba(47,100,248,0.35)",
              }}
            >
              IO
            </div>
            {!collapsed && (
              <span style={{ fontWeight: 700, fontSize: 13, color: "var(--text-primary)", whiteSpace: "nowrap" }}>
                Investor Ops
              </span>
            )}
          </Link>
          {!collapsed && (
            <button
              type="button"
              onClick={toggleCollapsed}
              aria-label="Collapse sidebar"
              title="Collapse sidebar"
              style={{
                background: "transparent",
                border: "1px solid var(--border-subtle)",
                borderRadius: 8,
                color: "var(--text-secondary)",
                cursor: "pointer",
                padding: "4px 6px",
                fontSize: 14,
                lineHeight: 1,
                flexShrink: 0,
              }}
            >
              «
            </button>
          )}
        </div>

        {collapsed && (
          <button
            type="button"
            onClick={toggleCollapsed}
            aria-label="Expand sidebar"
            title="Expand sidebar"
            style={{
              alignSelf: "center",
              background: "transparent",
              border: "1px solid var(--border-subtle)",
              borderRadius: 8,
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: "4px 8px",
              fontSize: 14,
              lineHeight: 1,
              marginBottom: 8,
            }}
          >
            »
          </button>
        )}

        {/* User nav */}
        <nav style={{ flex: 1, display: "flex", flexDirection: "column", gap: 2 }}>
          {!collapsed && (
            <p style={{ fontSize: 10, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", padding: "4px 14px", marginBottom: 4 }}>
              User
            </p>
          )}
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={`nav-link ${pathname === item.href ? "active" : ""}`}
              style={collapsed ? { justifyContent: "center", padding: "9px 0", gap: 0 } : undefined}
            >
              <span style={{ fontSize: 16 }}>{item.icon}</span>
              {!collapsed && item.label}
            </Link>
          ))}
        </nav>

        {/* Sign out */}
        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: 12, marginTop: 12 }}>
          <button
            id="sidebar-signout"
            onClick={signOut}
            title={collapsed ? "Sign out" : undefined}
            className="nav-link"
            style={{
              width: "100%",
              background: "none",
              border: "none",
              cursor: "pointer",
              textAlign: "left",
              ...(collapsed ? { justifyContent: "center", padding: "9px 0", gap: 0 } : {}),
            }}
          >
            <span style={{ fontSize: 16 }}>🚪</span>
            {!collapsed && "Sign out"}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ flex: 1, overflow: "auto" }}>{children}</main>
    </div>
  );
}
