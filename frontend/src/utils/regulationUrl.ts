/**
 * Normalize regulation source links from the API.
 * Local filesystem paths must be routed through /api/regulations/{filename},
 * prefixed with the configured API base so remote-API setups resolve correctly
 * (matches the prefixing in api/client.ts).
 */
const base = import.meta.env.VITE_API_BASE_URL ?? '';

export function resolveRegulationUrl(url: string): string | null {
  const trimmed = url.trim();
  if (!trimmed) return null;

  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }

  const filename = trimmed.split(/[/\\]/).pop();
  if (filename?.toLowerCase().endsWith('.pdf')) {
    return `${base}/api/regulations/${encodeURIComponent(filename)}`;
  }

  return null;
}
