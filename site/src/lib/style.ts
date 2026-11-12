import type { CSSProperties } from 'react';

/** Inline styles carried over exactly from the design reference (values may be CSS strings or vars). */
export const S = (o: Record<string, string | number | undefined>) => o as CSSProperties;

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && !!window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
