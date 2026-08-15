/**
 * J.A.R.V.I.S. v3.0 — Main App Component
 * Assembles the OLYMPUS command bridge:
 *   OlympusBackground (marble + atmosphere + rim)
 *   → Shell → TitleBar / [Sidebar | Main chat | ContextDrawer] / Composer
 *   + Settings overlay + White Room first-run
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { PanelRight } from 'lucide-react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { TitleBar } from '@/components/TitleBar';
import { Sidebar } from '@/components/Sidebar/Sidebar';
import { ActivityStream } from '@/components/ActivityStream/ActivityStream';
import { Composer } from '@/components/Composer';
import { ContextDrawer } from '@/components/ContextDrawer';
import { SettingsPanel } from '@/components/SettingsPanel';
import { CommandPalette } from '@/components/CommandPalette';
import { WhiteRoom } from '@/components/WhiteRoom';
import { OlympusBackground } from '@/components/Background/OlympusBackground';
import { useUIState } from '@/hooks/useUIState';
import { useBackendBridge } from '@/hooks/useBackendBridge';
import { useTheme } from '@/stores/themeStore';
import { useSessions } from '@/stores/sessionStore';
import type { AttachedFile } from '@/types';
import styles from './App.module.css';

function App() {
  const { dispatch, isSidebarOpen, isSettingsOpen } = useUIState();
  const { sendCommand, interrupt } = useBackendBridge();
  const { events } = useSessions();
  const { hasOnboarded } = useTheme();
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const isTauri = typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;

  const toggleFullscreen = async () => {
    if (isTauri) {
      try {
        const win = getCurrentWindow();
        const next = !isFullscreen;
        await win.setFullscreen(next);
        setIsFullscreen(next);
      } catch {
        // Tauri fullscreen unavailable — fall through to web fullscreen.
      }
      return;
    }
    // Web preview fallback: Fullscreen API.
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(Boolean(document.fullscreenElement));
    } else {
      await document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  // Global hotkeys: Ctrl/Cmd+K opens the palette; Esc closes it; F11 fullscreen.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const mod = event.ctrlKey || event.metaKey;
      if (mod && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen((prev) => !prev);
      } else if (event.key === 'F11') {
        event.preventDefault();
        void toggleFullscreen();
      } else if (event.key === 'Escape' && paletteOpen) {
        setPaletteOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [paletteOpen, isFullscreen]);

  const handleSend = (text: string, files: AttachedFile[]) => {
    if (!text.trim() && files.length === 0) return;
    sendCommand(text, files);
  };

  const lastCommand = useMemo(() => {
    for (let i = events.length - 1; i >= 0; i--) {
      if (events[i].kind === 'command') return events[i].content;
    }
    return undefined;
  }, [events]);

  const handleRetry = () => {
    if (lastCommand) sendCommand(lastCommand, []);
  };

  // Auto-open the context drawer the first time real execution appears.
  const openedRef = useRef(false);
  useEffect(() => {
    if (!openedRef.current && events.some((e) => e.kind === 'progress')) {
      openedRef.current = true;
      dispatch({ type: 'SET_DRAWER_OPEN', payload: true });
    }
  }, [events, dispatch]);

  return (
    <div className={styles.app}>
      <OlympusBackground />

      <div className={`${styles.shell} glass-shell`}>
        <TitleBar />

        <div className={styles.work}>
          {isSidebarOpen && <Sidebar />}

          <main className={styles.main}>
            <ActivityStream events={events} onRetry={handleRetry} />
          </main>

          <ContextDrawer events={events} />
        </div>

        <div className={styles.dock}>
          <div className={styles.dockSpacer} />
          <Composer onSend={handleSend} onStop={interrupt} />
          <button
            className={styles.drawerToggle}
            onClick={() => dispatch({ type: 'TOGGLE_DRAWER' })}
            aria-label="Открыть контекст"
            title="Контекст"
          >
            <PanelRight size={18} aria-hidden="true" />
          </button>
        </div>
      </div>

      {paletteOpen && (
        <CommandPalette
          isFullscreen={isFullscreen}
          onClose={() => setPaletteOpen(false)}
          onToggleFullscreen={() => void toggleFullscreen()}
          onToggleSidebar={() => dispatch({ type: 'TOGGLE_SIDEBAR' })}
          onToggleDrawer={() => dispatch({ type: 'TOGGLE_DRAWER' })}
          onOpenSettings={() => dispatch({ type: 'SET_SETTINGS_OPEN', payload: true })}
        />
      )}
      {isSettingsOpen && <SettingsPanel />}
      {!hasOnboarded && <WhiteRoom />}
    </div>
  );
}

export default App;
