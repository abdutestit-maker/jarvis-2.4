/**
 * J.A.R.V.I.S. v3.0 — CoreSymbol
 * The brand mark: a thin core with a couple of arcs. Small, never a giant logo.
 * Minimal motion (soft pulse + slow arc drift), gated by reduced-motion.
 */

import type { EntityState } from '@/types';
import styles from './CoreSymbol.module.css';

const STATE_CLASS: Record<string, string> = {
  idle: styles.idle,
  listening: styles.listening,
  thinking: styles.processing,
  executing: styles.processing,
  streaming: styles.processing,
  cloud: styles.cloud,
  error: styles.error,
};

interface Props {
  state?: EntityState;
  size?: number;
}

export function CoreSymbol({ state = 'idle', size = 18 }: Props) {
  const cls = STATE_CLASS[state] ?? styles.idle;
  return (
    <span
      className={`${styles.wrap} ${cls}`}
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 40 40" width={size} height={size}>
        <circle className={styles.arc2} cx="20" cy="20" r="14.5" />
        <circle className={styles.arc1} cx="20" cy="20" r="9" />
        <circle className={styles.core} cx="20" cy="20" r="3.1" />
      </svg>
    </span>
  );
}
