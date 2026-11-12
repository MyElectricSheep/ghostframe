import { useEffect, useState } from 'react';

/** True below 760 px, the page's "narrow" breakpoint. */
export const useNarrow = () => useMedia('(max-width: 759.98px)');

/** True while the media query matches. */
export function useMedia(query: string) {
  const [narrow, setNarrow] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setNarrow(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, [query]);
  return narrow;
}
