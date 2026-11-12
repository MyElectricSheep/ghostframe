import { S } from '../lib/style';

export function EntryLinks({ navHide, navRead }: { navHide: () => void; navRead: () => void }) {
  return (
<section id="start" data-screen-label="Use your own photo" style={S({ maxWidth: '1240px', margin: '0 auto', padding: '0 clamp(16px,4vw,40px) clamp(28px,4vw,44px)' })}>
  <div style={S({ display: 'flex', flexWrap: 'wrap', gap: '14px 28px', alignItems: 'center', justifyContent: 'space-between', padding: '18px 22px', background: '#fff', border: '1px solid rgba(24,20,17,0.10)', borderRadius: '8px' })}>
    <div style={S({ display: 'flex', flexDirection: 'column', gap: '4px', flex: '1 1 320px', minWidth: '0' })}>
      <span style={S({ fontSize: '16px', fontWeight: '700' })}>Try it with your own photo</span>
      <span style={S({ fontSize: '14px', lineHeight: '1.5', color: '#625c57', textWrap: 'pretty' })}>Hide a short message in a picture, or read one you were sent. Or start with the ready-made examples below.</span>
    </div>
    <div style={S({ flex: '0 1 auto', display: 'flex', flexWrap: 'wrap', gap: '8px' })}>
      <a href="#tool" onClick={navHide} style={S({ display: 'inline-flex', alignItems: 'center', gap: '8px', background: '#3f648c', color: '#fff', textDecoration: 'none', fontSize: '15px', fontWeight: '600', padding: '12px 18px', borderRadius: '4px' })} className="hover-primary-link">Hide a message</a>
      <a href="#tool" onClick={navRead} style={S({ display: 'inline-flex', alignItems: 'center', background: 'rgba(0,0,0,0.05)', color: 'rgba(18,16,14,0.96)', textDecoration: 'none', fontSize: '15px', fontWeight: '600', padding: '12px 16px', borderRadius: '4px' })} className="hover-secondary">Read a message</a>
    </div>
  </div>
</section>

  );
}

export function DashedRule() {
  return (
    <div aria-hidden="true" style={S({ maxWidth: '1240px', margin: '0 auto', padding: '0 clamp(16px,4vw,40px)' })}><div style={S({ borderTop: '1px dashed rgba(24,20,17,0.22)' })}></div></div>
  );
}
