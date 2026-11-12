// Daily encode counter (design option 9a, DAILY_COUNTER.md): the site-wide encodes left today, at
// the top right of "Use your own photo". Hidden when the count can't be read: never a guess.
import { useCallback, useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';
import { quota as fetchQuota } from '../../lib/api';
import type { Quota } from '../../lib/api';
import { useNarrow } from '../../hooks/useNarrow';
import { BLUE, INK, RED } from '../../data';
import { S } from '../../lib/style';

/** Fetches when the section first scrolls into view and whenever the tab becomes visible again;
 *  refresh() after each encode is accepted or ends; closed() when the encoder says the site limit is reached. */
export function useDailyQuota(section: RefObject<HTMLElement>) {
  const [q, setQ] = useState<Quota | null>(null);
  const seen = useRef(false), req = useRef(0);
  const refresh = useCallback(() => {
    if (!seen.current) return;
    const n = ++req.current;
    fetchQuota().then((v) => { if (n === req.current) setQ(v); }).catch(() => { if (n === req.current) setQ(null); });
  }, []);
  const closed = useCallback(() => { req.current++; setQ((v) => (v ? { ...v, left: 0 } : v)); refresh(); }, [refresh]);
  useEffect(() => {
    const el = section.current;
    if (!el) return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting) && !seen.current) { seen.current = true; refresh(); io.disconnect(); }
    });
    io.observe(el);
    const onVisible = () => { if (document.visibilityState === 'visible') refresh(); };
    document.addEventListener('visibilitychange', onVisible);
    return () => { io.disconnect(); document.removeEventListener('visibilitychange', onVisible); };
  }, [refresh]);
  return { q, refresh, closed };
}

export function DailyCounter({ q }: { q: Quota | null }) {
  const narrow = useNarrow();
  if (!q || !(q.limit > 0)) return null;
  const left = Math.max(0, Math.min(q.limit, q.left)), shut = left === 0, low = left > 0 && left <= 10;
  const align = narrow ? 'flex-start' : 'flex-end';
  return (
    <div style={S({ display: 'flex', flexDirection: 'column', alignItems: align, gap: '10px', marginLeft: narrow ? '0' : 'auto' })}>
      <div role="status" aria-live="polite" style={S({ display: 'flex', flexDirection: 'column', alignItems: align, gap: '6px' })}>
        <span style={S({ font: '500 13px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: shut ? RED : INK })}><strong style={S({ fontWeight: '600' })}>{left}</strong> / {q.limit} encodes left today</span>
        <div aria-hidden="true" style={S({ width: '170px', height: '4px', borderRadius: '2px', background: '#e0dad3', overflow: 'hidden' })}><div style={S({ height: '100%', width: (left / q.limit * 100) + '%', background: shut ? RED : low ? INK : BLUE, transition: 'width 300ms ease' })}></div></div>
        <span style={S({ fontSize: '11.5px', color: '#625c57' })}>{shut ? 'Closed until midnight UTC' : 'Shared by everyone · resets midnight UTC'}</span>
      </div>
    </div>
  );
}
