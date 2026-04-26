// Thin typed fetch wrapper for the FastAPI backend.
// Automatically attaches the active Supabase session token as a Bearer header.
import { createClient } from "@/lib/supabase/client";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function api<T = unknown>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = (await res.clone().json()) as { detail?: unknown };
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      try {
        detail = await res.text();
      } catch {
        // give up; the status code alone will surface in the error
      }
    }
    const suffix = detail ? ` — ${detail}` : "";
    throw new Error(`API ${path} failed: ${res.status}${suffix}`);
  }
  return res.json() as Promise<T>;
}
