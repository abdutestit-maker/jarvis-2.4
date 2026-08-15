/**
 * J.A.R.V.I.S. v3.0 — Rim Light
 * Cyan/gold ambient edge light that breathes with the entity state.
 */

import { useEffect, useRef } from 'react';
import { useUIState } from '@/hooks/useUIState';
import styles from './RimLight.module.css';

export function RimLight() {
  const { entityState } = useUIState();
  const glowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!glowRef.current) return;
    const durations: Record<string, string> = {
      idle: '5s', listening: '3.4s', thinking: '1.8s',
      executing: '2.2s', streaming: '2.6s', error: '1.2s', cloud: '3.6s',
    };
    const opacities: Record<string, string> = {
      idle: '0.5', listening: '0.7', thinking: '1', executing: '0.85',
      streaming: '0.9', error: '0.8', cloud: '0.75',
    };
    glowRef.current.style.animationDuration = durations[entityState] || '5s';
    glowRef.current.style.opacity = opacities[entityState] || '0.5';
  }, [entityState]);

  return (
    <div className={styles.container} aria-hidden="true">
      <div ref={glowRef} className={styles.glow} />
    </div>
  );
}
