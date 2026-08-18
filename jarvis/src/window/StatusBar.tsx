import { useEffect, useState } from 'react';
import type { PresenceState } from '@/bridge/StateMachine';

export function StatusBar({ state }: { state: PresenceState }) {
  const [time, setTime] = useState(() => clock());
  useEffect(() => { const id = window.setInterval(() => setTime(clock()), 1000); return () => window.clearInterval(id); }, []);
  return <header className="statusBar" data-tauri-drag-region>
    <span>JARVIS</span><time>{time}</time><i className={`presenceDot ${state}`} aria-label={state} />
  </header>;
}

function clock(): string { return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
