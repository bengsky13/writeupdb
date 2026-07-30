import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const API_BASE = process.env.INTERNAL_API_BASE ?? "http://backend:8000";

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const cookieStore = await cookies();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      Cookie: cookieStore.toString(),
      ...(init?.headers ?? {})
    }
  });
  if (response.status === 401) {
    redirect("/login");
  }
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
