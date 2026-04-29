"use client";

export function AuroraBackground() {
  return (
    <div
      className="fixed inset-0 pointer-events-none"
      style={{
        background:
          "radial-gradient(ellipse 80% 60% at 50% -20%, rgba(124,58,237,0.25) 0%, transparent 70%), " +
          "radial-gradient(ellipse 60% 40% at 80% 80%, rgba(6,182,212,0.15) 0%, transparent 60%)",
      }}
      aria-hidden
    />
  );
}
