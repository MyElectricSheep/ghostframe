import { useEffect, useRef, useState } from 'react';
import { S } from '../lib/style';
import { GhostLogo } from './GhostLogo';

/** One line at every width: the badge drops below 900 px and the nav scrolls sideways when it
 *  doesn't fit, with a fade on the side that has more links. */
function useNavFade() {
  const ref = useRef<HTMLElement>(null);
  const [fade, setFade] = useState('');
  useEffect(() => {
    const nav = ref.current;
    if (!nav) return;
    const update = () => {
      const more = nav.scrollWidth - nav.clientWidth;
      setFade(more <= 1 ? '' : nav.scrollLeft < 1 ? 'gf-fade-end' : nav.scrollLeft >= more - 1 ? 'gf-fade-start' : 'gf-fade-both');
    };
    update();
    nav.addEventListener('scroll', update, { passive: true });
    const ro = new ResizeObserver(update);
    ro.observe(nav);
    return () => { nav.removeEventListener('scroll', update); ro.disconnect(); };
  }, []);
  return [ref, fade] as const;
}

export function Header({ navHide, navRead }: { navHide: () => void; navRead: () => void }) {
  const [navRef, fade] = useNavFade();
  return (
<header style={S({ position: 'sticky', top: '0', zIndex: '30', background: '#f6f4f1', borderBottom: '1px solid rgba(24,20,17,0.10)' })}>
  <div style={S({ maxWidth: '1240px', margin: '0 auto', padding: '10px clamp(16px,4vw,40px)', display: 'flex', alignItems: 'center', gap: '10px 16px', flexWrap: 'nowrap' })}>
    <a href="#top" aria-label="Ghostframe, back to top" style={S({ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none', color: 'rgba(18,16,14,0.96)', '--gfa': 'rgba(18,16,14,0.96)', '--gfb': '#f6f4f1', flex: 'none' })} className="logo-invert logo-invert-focus">
      <GhostLogo />
      <span style={S({ fontWeight: '700', fontSize: '16px', letterSpacing: '-0.2px' })}>Ghostframe</span>
    </a>
    <span style={S({ font: '500 11px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57', border: '1px dashed rgba(24,20,17,0.30)', padding: '4px 8px', borderRadius: '999px', whiteSpace: 'nowrap', flex: 'none' })} className="gf-badge">engineering experiment</span>
    <nav ref={navRef} aria-label="Sections" style={S({ marginLeft: 'auto', display: 'flex', gap: '2px', flexWrap: 'nowrap', minWidth: '0', overflowX: 'auto' })} className={'gf-nav ' + fade}>
      <a href="#try" style={S({ fontSize: '14px', fontWeight: '600', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', padding: '8px 10px', borderRadius: '4px' })} className="hover-tint">Try it</a>
      <a href="#tool" onClick={navHide} style={S({ fontSize: '14px', fontWeight: '600', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', padding: '8px 10px', borderRadius: '4px' })} className="hover-tint">Hide</a>
      <a href="#tool" onClick={navRead} style={S({ fontSize: '14px', fontWeight: '600', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', padding: '8px 10px', borderRadius: '4px' })} className="hover-tint">Read</a>
      <a href="#how" style={S({ fontSize: '14px', fontWeight: '600', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', padding: '8px 10px', borderRadius: '4px' })} className="hover-tint">How it works</a>
      <a href="#limits" style={S({ fontSize: '14px', fontWeight: '600', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', padding: '8px 10px', borderRadius: '4px' })} className="hover-tint">Limits and evidence</a>
    </nav>
  </div>
</header>

  );
}
