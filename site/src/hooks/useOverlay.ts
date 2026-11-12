import { useEffect } from 'react';
import type { RefObject } from 'react';

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Phone menu and bottom sheet: while open, the page behind doesn't scroll, Escape
 * closes, focus moves into the panel and Tab stays inside it (plus `keep`, e.g. the burger that
 * closes it). On close, focus returns to `back`.
 */
export function useOverlay(open: boolean, close: () => void, panel: RefObject<HTMLElement>, back: RefObject<HTMLElement>, keep?: RefObject<HTMLElement>) {
  useEffect(() => {
    if (!open) return;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const focusables = () => [...(keep?.current ? [keep.current] : []), ...(panel.current ? [...panel.current.querySelectorAll<HTMLElement>(FOCUSABLE)] : [])];
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); close(); return; }
      if (e.key !== 'Tab') return;
      const f = focusables();
      if (!f.length) return;
      const i = f.indexOf(document.activeElement as HTMLElement);
      if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
      else if (!e.shiftKey && (i === -1 || i === f.length - 1)) { e.preventDefault(); f[0].focus(); }
    };
    document.addEventListener('keydown', onKey);
    // After the panel becomes visible: focus its marked element, or its first control.
    const raf = requestAnimationFrame(() => {
      const target = panel.current?.querySelector<HTMLElement>('[data-autofocus]') ?? panel.current?.querySelector<HTMLElement>(FOCUSABLE);
      target?.focus({ preventScroll: true });
    });
    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = overflow;
      back.current?.focus({ preventScroll: true });
    };
  }, [open]);
}
