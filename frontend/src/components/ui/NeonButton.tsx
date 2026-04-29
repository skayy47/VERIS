"use client";

import { motion } from "framer-motion";
import type { ButtonHTMLAttributes } from "react";

interface NeonButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary";
}

export function NeonButton({
  children,
  variant = "primary",
  className = "",
  style,
  ...props
}: NeonButtonProps) {
  const baseStyle =
    variant === "primary"
      ? { backgroundColor: "var(--color-accent)", color: "#fff" }
      : { border: "1px solid var(--color-accent)", color: "var(--color-accent)" };

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`px-4 py-2 rounded text-sm font-medium transition-opacity disabled:opacity-40 disabled:cursor-not-allowed ${className}`}
      style={{ ...baseStyle, ...style }}
      {...(props as any)}
    >
      {children}
    </motion.button>
  );
}
