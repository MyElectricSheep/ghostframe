import { useEffect, useState } from 'react';

/** True below 760 px, the design's "narrow" breakpoint. */
export function useNarrow() {
  const query = '(max-width: 759.98px)';
  const [narrow, setNarrow] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const on = () => setNarrow(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return narrow;
}
