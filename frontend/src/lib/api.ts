import type { AgentStateUpdate, ResearchRequest } from "./types";

const API_BASE = "/api";

export async function postResearch(req: ResearchRequest): Promise<Response> {
  return fetch(`${API_BASE}/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
}

export async function getMetrics(sessionId: string): Promise<Response> {
  return fetch(`${API_BASE}/metrics/${sessionId}`);
}

// EventSource-based helper for GET endpoints (kept for future GET-compatible stream)
// TODO(W3): consolidate with postResearch stream consumer once routing is stable
export function streamResearch(
  req: ResearchRequest,
  onUpdate: (update: AgentStateUpdate) => void,
  onError: (err: Event) => void,
  onDone: () => void
): EventSource {
  const params = new URLSearchParams({
    query: req.query,
    language: req.language ?? "en",
    max_steps: String(req.max_steps ?? 8),
  });
  const source = new EventSource(`${API_BASE}/research?${params}`);
  source.onmessage = (evt) => {
    try {
      const update: AgentStateUpdate = JSON.parse(evt.data);
      onUpdate(update);
      if (update.state === "done" || update.state === "answer") {
        source.close();
        onDone();
      }
    } catch {
      // skip malformed SSE frame
    }
  };
  source.onerror = (err) => {
    onError(err);
    source.close();
    onDone();
  };
  return source;
}
