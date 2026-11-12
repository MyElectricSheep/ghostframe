import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type React from 'react';
import { ABBR } from '../data';
import type { AbbrKey } from '../data';
import { S } from '../lib/style';

type Open = Record<AbbrKey, (e: React.MouseEvent<HTMLElement>) => void>;
type Expanded = Record<AbbrKey, boolean>;
const Ctx = createContext<{ abOpen: Open; abExp: Expanded } | null>(null);

/** Acronym tooltips (PSNR, SSIM, AES-256-GCM, scrypt): open on click or tap, close on outside click, Esc or scroll. */
export function AbbrProvider({ children }: { children: React.ReactNode }) {
  const [ab, setAb] = useState<{ k: AbbrKey; x: number; y: number } | null>(null);
  const open = useCallback((k: AbbrKey, e: React.MouseEvent<HTMLElement>) => {
    const r = e.currentTarget.getBoundingClientRect(), W = 260, below = r.bottom + 130 < window.innerHeight;
    const x = Math.max(12, Math.min(window.innerWidth - W - 12, r.left + r.width / 2 - W / 2));
    setAb((cur) => (cur && cur.k === k ? null : { k, x, y: below ? r.bottom + 8 : Math.max(12, r.top - 8 - 120) }));
  }, []);
  useEffect(() => {
    if (!ab) return;
    const close = (ev: Event) => {
      if (ev.type === 'keydown' && (ev as KeyboardEvent).key !== 'Escape') return;
      const t = ev.target as Element | null;
      if (ev.type === 'pointerdown' && t && t.closest && (t.closest('[data-abbr]') || t.closest('#gf-abbr'))) return;
      setAb(null);
    };
    document.addEventListener('pointerdown', close); document.addEventListener('keydown', close); window.addEventListener('scroll', close, { passive: true });
    return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', close); window.removeEventListener('scroll', close); };
  }, [ab]);
  const value = useMemo(() => {
    const keys = Object.keys(ABBR) as AbbrKey[];
    return {
      abOpen: Object.fromEntries(keys.map((k) => [k, (e: React.MouseEvent<HTMLElement>) => open(k, e)])) as Open,
      abExp: Object.fromEntries(keys.map((k) => [k, ab?.k === k])) as Expanded,
    };
  }, [ab, open]);
  const abX = (ab?.x || 0) + 'px', abY = (ab?.y || 0) + 'px', abDisp = ab ? 'flex' : 'none';
  const abTitle = ab ? ABBR[ab.k][0] : '', abText = ab ? ABBR[ab.k][1] : '';
  return (
    <Ctx.Provider value={value}>
      {children}
<div id="gf-abbr" role="tooltip" style={S({ position: 'fixed', left: abX, top: abY, width: '260px', boxSizing: 'border-box', padding: '12px 14px', background: '#312e2b', color: '#f6f4f1', borderRadius: '8px', boxShadow: '0 8px 24px rgba(0,0,0,0.25)', zIndex: '60', display: abDisp, flexDirection: 'column', gap: '5px' })}>
  <span style={S({ font: '600 13px/1.25 Inter,sans-serif' })}>{abTitle}</span>
  <span style={S({ fontSize: '12.5px', lineHeight: '1.5', textWrap: 'pretty' })}>{abText}</span>
</div>

    </Ctx.Provider>
  );
}

export function useAbbr() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAbbr outside AbbrProvider');
  return v;
}
