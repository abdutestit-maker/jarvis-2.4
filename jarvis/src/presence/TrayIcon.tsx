import { useEffect } from 'react';
import type { PresenceState } from '@/bridge/StateMachine';
export function TrayIcon({ onHotkey, state: _state }: { onHotkey: () => void; state: PresenceState }) { useEffect(() => { const listener = () => onHotkey(); window.addEventListener('jarvis:hotkey', listener); return () => window.removeEventListener('jarvis:hotkey', listener); }, [onHotkey]); return null; }
