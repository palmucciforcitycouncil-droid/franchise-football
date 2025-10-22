// Minimal fetch wrapper + fallback helper (no framework dependency)
import { BASE_API, REQUEST_TIMEOUT_MS } from "../config.js";

function timeout(ms) {
  return new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), ms));
}

export async function fetchJson(path) {
  const url = path.startsWith("http") ? path : `${BASE_API}${path}`;
  const res = await Promise.race([
    fetch(url, { headers: { "Accept": "application/json" } }),
    timeout(REQUEST_TIMEOUT_MS),
  ]);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${text}`);
  }
  return res.json();
}

export async function withDemo(promise, demo) {
  try {
    const data = await promise;
    if (!data || (Array.isArray(data) && data.length === 0)) {
      return { data: demo, demo: true, error: "empty" };
    }
    return { data, demo: false, error: null };
  } catch (e) {
    return { data: demo, demo: true, error: String(e.message || e) };
  }
}

