import { useEffect, useRef, useState } from 'react';
import { useNarrow } from '../hooks/useNarrow';
import { useOverlay } from '../hooks/useOverlay';
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

const MENU = [
  { n: '01', t: 'Try it', d: 'Spot the difference in three photos', href: '#try' },
  { n: '02', t: 'How it works', d: 'Five steps, each animated', href: '#how' },
  { n: '03', t: 'Hide a message', d: 'In your own photo', href: '#tool', tab: 'hide' },
  { n: '04', t: 'Read a message', d: 'From a PNG you were sent', href: '#tool', tab: 'read' },
  { n: '05', t: 'Limits and evidence', d: 'What it can’t do, and the numbers', href: '#limits' },
] as const;

/** Phone menu: a burger opens a full-screen list of the sections under the header. */
function PhoneMenu({ navHide, navRead }: { navHide: () => void; navRead: () => void }) {
  const [open, setOpen] = useState(false);
  const burger = useRef<HTMLButtonElement>(null), panel = useRef<HTMLDivElement>(null);
  const [top, setTop] = useState(0);
  useOverlay(open, () => setOpen(false), panel, burger, burger);
  useEffect(() => { if (open) setTop(burger.current?.closest('header')?.getBoundingClientRect().bottom ?? 0); }, [open]);
  const go = (tab?: string) => () => {
    // Close first, so the page can scroll again, then let the link navigate.
    document.body.style.overflow = '';
    setOpen(false);
    if (tab === 'hide') navHide(); else if (tab === 'read') navRead();
  };
  return (
    <>
      <button ref={burger} type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="gf-menu" aria-label={open ? 'Close menu' : 'Open menu'} style={S({ marginLeft: 'auto', marginRight: '-8px', width: '44px', height: '44px', flex: 'none', border: '0', background: 'none', borderRadius: '6px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(18,16,14,0.96)', cursor: 'pointer' })}>
        {open
          ? <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><path d="M5 5l12 12M17 5L5 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>
          : <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true"><path d="M3 6h16M3 11h16M3 16h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg>}
      </button>
      <div ref={panel} id="gf-menu" style={S({ position: 'fixed', top: top + 'px', left: '0', right: '0', bottom: '0', zIndex: '29', background: '#f6f4f1', borderTop: '1px solid rgba(24,20,17,0.10)', display: 'flex', flexDirection: 'column', overflowY: 'auto', overscrollBehavior: 'contain', transition: `opacity 220ms ease, transform 220ms ease, visibility 0s linear ${open ? '0s' : '220ms'}`, opacity: open ? '1' : '0', transform: open ? 'translateY(0)' : 'translateY(-8px)', pointerEvents: open ? 'auto' : 'none', visibility: open ? 'visible' : 'hidden' })}>
        <nav aria-label="Sections" style={S({ display: 'flex', flexDirection: 'column', padding: '8px 0' })}>
          {MENU.map((l) => (
            <a key={l.n} href={l.href} onClick={go('tab' in l ? l.tab : undefined)} style={S({ display: 'flex', alignItems: 'baseline', gap: '14px', padding: '18px 20px', borderBottom: '1px solid rgba(24,20,17,0.10)', textDecoration: 'none', color: 'rgba(18,16,14,0.96)' })}>
              <span style={S({ font: '500 12px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#3f648c', width: '20px', flex: 'none' })}>{l.n}</span>
              <span style={S({ display: 'flex', flexDirection: 'column', gap: '4px' })}><span style={S({ fontSize: '24px', fontWeight: '700', letterSpacing: '-0.3px' })}>{l.t}</span><span style={S({ fontSize: '13.5px', color: '#625c57' })}>{l.d}</span></span>
            </a>
          ))}
        </nav>
        <p style={S({ margin: '0', padding: '20px', fontSize: '13px', lineHeight: '1.5', color: '#625c57' })}>Ghostframe is an engineering experiment by <a href="https://electricsheep.id" target="_blank" rel="noopener">Ben Paget</a>.</p>
      </div>
    </>
  );
}

export function Header({ navHide, navRead }: { navHide: () => void; navRead: () => void }) {
  const [navRef, fade] = useNavFade();
  // Below 760 px the burger replaces the nav row; the menu unmounts (and so closes) above it.
  const narrow = useNarrow();
  return (
<header style={S({ position: 'sticky', top: '0', zIndex: '30', background: '#f6f4f1', borderBottom: '1px solid rgba(24,20,17,0.10)' })}>
  <div style={S({ maxWidth: '1240px', margin: '0 auto', padding: '10px clamp(16px,4vw,40px)', display: 'flex', alignItems: 'center', gap: '10px 16px', flexWrap: 'nowrap' })}>
    <a href="#top" aria-label="Ghostframe, back to top" style={S({ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none', color: 'rgba(18,16,14,0.96)', '--gfa': 'rgba(18,16,14,0.96)', '--gfb': '#f6f4f1', flex: 'none' })} className="logo-invert logo-invert-focus">
      <GhostLogo />
      <span style={S({ fontWeight: '700', fontSize: '16px', letterSpacing: '-0.2px' })}>Ghostframe</span>
    </a>
    <span style={S({ font: '500 11px/1 \'IBM Plex Mono\',ui-monospace,monospace', color: '#625c57', border: '1px dashed rgba(24,20,17,0.30)', padding: '4px 8px', borderRadius: '999px', whiteSpace: 'nowrap', flex: 'none' })} className="gf-badge">engineering experiment</span>
    {narrow ? <PhoneMenu navHide={navHide} navRead={navRead} /> : (<nav ref={navRef} aria-label="Sections" style={S({ marginLeft: 'auto', display: 'flex', gap: '2px', flexWrap: 'nowrap', minWidth: '0', overflowX: 'auto' })} className={'gf-nav ' + fade}>
      <a href="#try" style={S({ fontSize: '14px', fontWeight: '600', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', padding: '8px 10px', borderRadius: '4px' })} className="hover-tint">Try it</a>
      <a href="#tool" onClick={navHide} style={S({ fontSize: '14px', fontWeight: '600', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', padding: '8px 10px', borderRadius: '4px' })} className="hover-tint">Hide</a>
      <a href="#tool" onClick={navRead} style={S({ fontSize: '14px', fontWeight: '600', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', padding: '8px 10px', borderRadius: '4px' })} className="hover-tint">Read</a>
      <a href="#how" style={S({ fontSize: '14px', fontWeight: '600', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', padding: '8px 10px', borderRadius: '4px' })} className="hover-tint">How it works</a>
      <a href="#limits" style={S({ fontSize: '14px', fontWeight: '600', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', padding: '8px 10px', borderRadius: '4px' })} className="hover-tint">Limits and evidence</a>
    </nav>)}
  </div>
</header>

  );
}
