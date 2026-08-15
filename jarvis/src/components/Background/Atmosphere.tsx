/**
 * J.A.R.V.I.S. v3.0 — Atmosphere Layer
 * Smoky, slowly drifting gradients that give the OS-window depth.
 * Combined with Hermes + RimLight = living background.
 */

import { useUIState } from '@/hooks/useUIState';
import styles from './Atmosphere.module.css';

export function Atmosphere() {
  const { entityState } = useUIState();
  // a touch more energy while working
  const active = entityState === 'thinking' || entityState === 'executing' || entityState === 'streaming';

  return (
    <div className={`${styles.layer} ${active ? styles.active : ''}`} aria-hidden="true">
      <div className={styles.g1} />
      <div className={styles.g2} />
      <div className={styles.g3} />
      <div className={styles.grain} />
    </div>
  );
}
