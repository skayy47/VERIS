"use client";

import { AnimatePresence, motion } from "framer-motion";
import { GlowCard } from "@/components/ui/GlowCard";
import type { AgentStateUpdate } from "@/lib/types";

const STATE_LABELS: Record<string, string> = {
  plan: "Planning",
  search: "Searching",
  reason: "Reasoning",
  verify: "Verifying",
  answer: "Answer",
  done: "Done",
  error: "Error",
};

interface StreamingReasoningProps {
  steps: AgentStateUpdate[];
  isStreaming: boolean;
}

export function StreamingReasoning({ steps, isStreaming }: StreamingReasoningProps) {
  if (!steps.length && !isStreaming) return null;

  return (
    <GlowCard>
      <p
        className="text-xs uppercase tracking-wider mb-3"
        style={{ color: "var(--color-muted)" }}
      >
        Reasoning Steps
      </p>
      <div className="flex flex-col gap-2">
        <AnimatePresence initial={false}>
          {steps.map((step) => (
            <motion.div
              key={step.step_index}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex gap-3 text-sm"
            >
              <span
                className="shrink-0 w-24"
                style={{ color: "var(--color-accent)" }}
              >
                [{STATE_LABELS[step.state] ?? step.state}]
              </span>
              <span style={{ color: "var(--color-text)" }}>{step.content}</span>
            </motion.div>
          ))}
        </AnimatePresence>
        {isStreaming && (
          <motion.div
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ repeat: Infinity, duration: 1.5 }}
            className="text-xs"
            style={{ color: "var(--color-muted)" }}
          >
            Processing...
          </motion.div>
        )}
      </div>
    </GlowCard>
  );
}
