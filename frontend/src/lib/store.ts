import { create } from "zustand";
import type { AgentStateUpdate, Citation, Metrics } from "./types";

interface ResearchState {
  sessionId: string | null;
  isStreaming: boolean;
  steps: AgentStateUpdate[];
  citations: Citation[];
  metrics: Metrics | null;
  error: string | null;
  setSessionId: (id: string) => void;
  setStreaming: (streaming: boolean) => void;
  appendStep: (update: AgentStateUpdate) => void;
  setCitations: (citations: Citation[]) => void;
  setMetrics: (metrics: Metrics) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useResearchStore = create<ResearchState>((set) => ({
  sessionId: null,
  isStreaming: false,
  steps: [],
  citations: [],
  metrics: null,
  error: null,
  setSessionId: (id) => set({ sessionId: id }),
  setStreaming: (streaming) => set({ isStreaming: streaming }),
  appendStep: (update) => set((s) => ({ steps: [...s.steps, update] })),
  setCitations: (citations) => set({ citations }),
  setMetrics: (metrics) => set({ metrics }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      sessionId: null,
      isStreaming: false,
      steps: [],
      citations: [],
      metrics: null,
      error: null,
    }),
}));
