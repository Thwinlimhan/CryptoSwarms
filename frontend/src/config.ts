export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

/** WebSocket base URL derived from API_URL (http(s) -> ws(s)). Override with VITE_WS_URL. */
export function getWebSocketBaseUrl(): string {
  const envWs = import.meta.env.VITE_WS_URL;
  if (envWs) return envWs;
  if (!API_URL || API_URL === '') {
    // Same-origin (e.g. Vite proxy): use current host so /ws is proxied
    if (typeof window !== 'undefined') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${protocol}//${window.location.host}`;
    }
    return 'ws://127.0.0.1:8000';
  }
  return API_URL.replace(/^http/, 'ws');
}
