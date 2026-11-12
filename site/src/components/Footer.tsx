import { S } from '../lib/style';

export function Footer() {
  return (
<footer style={S({ background: '#f6f4f1' })}>
  <div style={S({ maxWidth: '1240px', margin: '0 auto', padding: '24px clamp(16px,4vw,40px) 40px', display: 'flex', flexWrap: 'wrap', gap: '10px 32px', justifyContent: 'space-between', fontSize: '12.5px', lineHeight: '1.55', color: '#625c57' })}>
    <span style={S({ maxWidth: '36em', display: 'flex', flexDirection: 'column', gap: '4px' })}><span>Ghostframe is an engineering experiment by <a href="https://electricsheep.id" target="_blank" rel="noopener">Ben Paget</a>.</span><span>No accounts, nothing stored. Don’t use it to hide illegal content.</span></span>
    <span style={S({ maxWidth: '40em' })}>Antonello da Messina, Portrait of a Man (about 1475), The National Gallery, London, public domain. “Roasted coffee beans” by MarkSweep, public domain. “Milky Way Night Sky” by Guillaume (Unsplash), CC0. Upload sample “Wellington Railway Station, NSW Platform” by Abesty, CC0. All via Wikimedia Commons.</span>
  </div>
</footer>

  );
}
