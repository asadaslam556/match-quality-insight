const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function get<T>(path: string, params: Record<string, string> = {}): Promise<T> {
  const query = new URLSearchParams(params).toString();
  const response = await fetch(`${BASE}/api/${path}${query ? `?${query}` : ""}`);
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`);
  }
  return response.json();
}
