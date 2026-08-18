/**
 * J.A.R.V.I.S. v3.0 — TitleBar
 * Minimal frameless header: CoreSymbol + wordmark + live state, window controls.
 * No permanent telemetry (CPU/RAM dashboards are removed per spec).
 */

import { useEffect } from 'react';
import { Minimize, Square, X } from 'lucide-react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { invoke } from '@tauri-apps/api/core';
import { useUIState } from '@/hooks/useUIState';
import { CoreSymbol } from '@/components/CoreSymbol/CoreSymbol';
import { STATE_LABEL } from '@/integrations/backend';
import styles from './TitleBar.module.css';

const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
const appWindow = isTauri ? getCurrentWindow() : null;

export function TitleBar() {
  const { entityState } = useUIState();

  useEffect(() => {
    invoke('set_window_effect', { effect: 'acrylic' }).catch(() => {});
  }, []);

  return (
    <header className={`${styles.bar} drag-region`} role="banner" data-tauri-drag-region>
      <div className={styles.left} data-tauri-drag-region>
        <CoreSymbol state={entityState} size={18} />
        <span className={styles.word}>J.A.R.V.I.S.</span>
        <span className={styles.state} data-state={entityState}>
          <span className={styles.stateDot} aria-hidden="true" />
          {STATE_LABEL[entityState] ?? 'ONLINE'}
        </span>
      </div>

      <div className={styles.center} data-tauri-drag-region />

      <div className={styles.controls} data-tauri-drag-region="false">
        <button className={styles.ctrl} onClick={() => appWindow?.minimize()} aria-label="Свернуть">
          <Minimize size={13} />
        </button>
        <button className={styles.ctrl} onClick={() => appWindow?.toggleMaximize()} aria-label="Развернуть">
          <Square size={12} />
        </button>
        <button
          className={styles.ctrl}
          onClick={async () => {
            if (!appWindow) return;
            try {
              const fs = await appWindow.isFullscreen();
              await appWindow.setFullscreen(!fs);
            } catch { /* fullscreen unavailable */ }
          }}
          aria-label="Полноэкранный режим"
          title="Полноэкранный режим (F11)"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
        </button>
        <button className={`${styles.ctrl} ${styles.close}`} onClick={() => appWindow?.close()} aria-label="Закрыть">
          <X size={13} />
        </button>
      </div>
    </header>
  );
}
