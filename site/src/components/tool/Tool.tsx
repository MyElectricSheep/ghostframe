import React, { useRef } from 'react';
import type { Tab } from '../../App';
import { BLUE, GRAY, INK } from '../../data';
import { S } from '../../lib/style';
import { openPrivacy } from '../Footer';
import { DailyCounter, useDailyQuota } from './DailyCounter';
import { HideTab } from './HideTab';
import { ReadTab } from './ReadTab';

export function Tool({ tab, setTab }: { tab: Tab; setTab: (t: Tab) => void }) {
  const tabs = ([['hide', 'Hide a message'], ['read', 'Read a message']] as [Tab, string][]).map(([id, label]) => ({
    id: 'gf-tab-' + id, label, selected: tab === id, tabIndex: tab === id ? 0 : -1, bar: tab === id ? BLUE : 'transparent', fg: tab === id ? INK : GRAY, onClick: () => setTab(id),
  }));
  const onTabKey = (e: React.KeyboardEvent) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    const t: Tab = tab === 'hide' ? 'read' : 'hide';
    setTab(t);
    setTimeout(() => document.getElementById('gf-tab-' + t)?.focus(), 0);
  };
  const tabLabelledBy = 'gf-tab-' + tab;
  const sectionRef = useRef<HTMLElement>(null);
  const quota = useDailyQuota(sectionRef);
  return (
<section ref={sectionRef} id="tool" data-screen-label="Hide and read" style={S({ background: '#fff', borderTop: '1px dashed rgba(24,20,17,0.22)', borderBottom: '1px dashed rgba(24,20,17,0.22)', scrollMarginTop: '56px' })}>
  <div style={S({ maxWidth: '1240px', margin: '0 auto', padding: 'clamp(32px,5vw,56px) clamp(16px,4vw,40px)', display: 'flex', flexDirection: 'column', gap: '22px' })}>
    <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '12px 32px', alignItems: 'flex-end', justifyContent: 'space-between' })}>
      <div style={S({ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '40em' })}>
        <h2 style={S({ margin: '0', fontSize: 'clamp(28px,3.4vw,40px)', fontWeight: '700', letterSpacing: '-0.02em', lineHeight: '1.1' })}>Use your own photo</h2>
        <p style={S({ margin: '0', fontSize: '16px', lineHeight: '1.55', color: '#625c57', textWrap: 'pretty' })}>Your photo, message and passphrase are sent to the demo server and processed in memory only; they are never written to disk and never shared. The result is deleted from the server as soon as your browser has fetched it, or after 15 minutes at most. <a href="#privacy" onClick={openPrivacy}>Privacy</a></p>
      </div>
      <DailyCounter q={quota.q} />
    </div>

    <div role="tablist" aria-label="Hide or read" onKeyDown={onTabKey} style={S({ display: 'flex', borderBottom: '1px solid rgba(24,20,17,0.10)' })}>
      {tabs.map((tb, i) => (<React.Fragment key={i}>
        <button type="button" role="tab" id={tb.id} aria-selected={tb.selected} aria-controls="gf-tabpanel" tabIndex={tb.tabIndex} onClick={tb.onClick} style={S({ fontSize: '16px', fontWeight: '600', padding: '14px 16px', background: 'transparent', border: '0', borderBottom: `2px solid ${tb.bar}`, marginBottom: '-1px', color: tb.fg, cursor: 'pointer' })}>{tb.label}</button>
      </React.Fragment>))}
    </div>

    <div id="gf-tabpanel" role="tabpanel" aria-labelledby={tabLabelledBy}>
    {/* Both tabs stay mounted so a running encode keeps polling while the reader is open. */}
    <div hidden={tab !== 'hide'}><HideTab navRead={() => setTab('read')} quota={quota} /></div>
    <div hidden={tab !== 'read'}><ReadTab /></div>
    </div>
  </div>
</section>
  );
}
