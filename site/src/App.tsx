import { useState } from 'react';
import { DashedRule, EntryLinks } from './components/EntryLinks';
import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { Reveal } from './components/Reveal';
import { TryIt } from './components/try/TryIt';
import { initialTryIt } from './components/try/view';
import type { TryItState } from './components/try/view';
import type { ModeKey, PhotoKey } from './data';
import { S } from './lib/style';

export type Tab = 'hide' | 'read';

export function App() {
  const [, setTab] = useState<Tab>('hide');
  const [tryIt, setTryIt] = useState<TryItState>({ photo: 'antonello', mode: 'subtle', ...initialTryIt() });
  const setTry = (patch: Partial<TryItState>) => setTryIt((s) => ({ ...s, ...patch }));
  const pick = (photo: PhotoKey, mode: ModeKey) => setTry({ photo, mode, sel: null });
  const navHide = () => setTab('hide');
  const navRead = () => setTab('read');
  return (
    <div style={S({ minHeight: '100vh', background: '#f6f4f1' })}>
      <Header navHide={navHide} navRead={navRead} />
      <Hero />
      <EntryLinks navHide={navHide} navRead={navRead} />
      <DashedRule />
      <TryIt state={tryIt} set={setTry} pick={pick} />
      {/* Changing cover, mode or view resets the reveal, as in the design. */}
      <Reveal key={`${tryIt.photo}|${tryIt.mode}|${tryIt.view}`} photo={tryIt.photo} mode={tryIt.mode} />
      <DashedRule />
    </div>
  );
}
