/**
 * J.A.R.V.I.S. v3.0 — Olympus Marble
 * Antique marble bust, positioned to the SIDE (never center of text),
 * heavily darkened + low saturation, swappable asset (no backend dependency).
 *
 * Default asset: /assets/athena.svg
 * Personal theme may override via ThemeProvider --personal-bg.
 */

import { useEffect, useRef } from 'react';
import { useUIState } from '@/hooks/useUIState';
import { useTheme } from '@/stores/themeStore';
import styles from './OlympusMarble.module.css';

const OPACITY: Record<string, number> = {
  idle: 0.12, listening: 0.14, thinking: 0.20, executing: 0.18,
  streaming: 0.16, error: 0.22, cloud: 0.16,
};

export function OlympusMarble() {
  const { entityState } = useUIState();
  const { settings } = useTheme();
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    if (imgRef.current) {
      imgRef.current.style.opacity = String(OPACITY[entityState] ?? 0.14);
    }
  }, [entityState]);

  const src = settings.backgroundUrl ?? '/assets/athena.svg';

  return (
    <div className={styles.container} aria-hidden="true">
      <img
        ref={imgRef}
        className={styles.statue}
        src={src}
        alt=""
        loading="lazy"
      />
      <div className={styles.glow} />
    </div>
  );
}
