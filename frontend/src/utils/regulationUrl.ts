/**
 * Normalize regulation source links from the API.
 * Local filesystem paths must be routed through /api/regulations/{filename}.
 */
export function resolveRegulationUrl(url: string): string | null {
  const trimmed = url.trim();
  if (!trimmed) return null;

  if (/^https?:\/\//i.test(trimmed)) {
    return trimmed;
  }

  const filename = trimmed.split(/[/\\]/).pop();
  if (filename?.toLowerCase().endsWith('.pdf')) {
    return `/api/regulations/${encodeURIComponent(filename)}`;
  }

  return null;
}
