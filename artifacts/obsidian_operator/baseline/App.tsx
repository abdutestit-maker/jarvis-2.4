import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { StateMachine, presenceFromTransport, type PresenceState } from '@/bridge/StateMachine';
import { TTSController } from '@/bridge/TTSController';
import { TrayIcon } from '@/presence/TrayIcon';
import { InputOverlay } from '@/overlay/InputOverlay';
import { MainWindow } from '@/window/MainWindow';
import type { PresenceMessage } from '@/window/MessageStream';
import { WebSocketBackend } from '@/integrations/wsBackend';
import type { BackendEvent } from '@/types';
import './presence.css';

function isOverlayWindow(): boolean {
  try { return getCurrentWindow().label === 'overlay'; } catch { return false; }
}

function App() {
  const backend = useMemo(() => new WebSocketBackend('ws://127.0.0.1:8771'), []);
  const machine = useMemo(() => new StateMachine(), []);
  const tts = useMemo(() => new TTSController(), []);
  const [messages, setMessages] = useState<PresenceMessage[]>([]);
  const [state, setState] = useState<PresenceState>('idle');
  const [firstLaunch, setFirstLaunch] = useState(false);
  const streaming = useRef<string | null>(null);
  const overlay = isOverlayWindow();

  const transition = useCallback((next: PresenceState) => setState(machine.transition(next)), [machine]);
  const append = useCallback((message: PresenceMessage) => setMessages((current) => [...current, message].slice(-20)), []);
  const closeOverlay = useCallback(() => { try { void getCurrentWindow().hide(); } catch { /* browser preview */ } }, []);

  useEffect(() => backend.subscribeToEvents((event: BackendEvent) => {
    if (event.type.startsWith('state:')) { transition(presenceFromTransport(event.type.slice(6))); return; }
    if (event.type === 'profile:status') { setFirstLaunch(!(event.payload as { hasName: boolean }).hasName); return; }
    if (event.type === 'event:voice_input') {
      const payload = event.payload as { text: string; confidence: number };
      if (payload.confidence >= 0.7 && payload.text.trim()) { append({ id: `voice-${Date.now()}`, role: 'user', text: payload.text, timestamp: Date.now() }); transition('thinking'); void backend.sendCommand(payload.text, []); }
      return;
    }
    if (event.type === 'event:jarvis:start') {
      const payload = event.payload as { id: string }; streaming.current = payload.id;
      append({ id: payload.id, role: 'jarvis', text: '', timestamp: event.timestamp }); transition('thinking'); return;
    }
    if (event.type === 'event:jarvis:token' || event.type === 'event:jarvis:end') {
      const payload = event.payload as { id: string; content?: string; token?: string };
      const text = payload.content ?? payload.token ?? '';
      setMessages((current) => current.map((message) => message.id === (streaming.current ?? payload.id) ? { ...message, text } : message));
      if (event.type === 'event:jarvis:end') { streaming.current = null; tts.finish(); transition('idle'); }
    }
  }), [append, backend, transition, tts]);

  useEffect(() => {
    let off: (() => void) | undefined;
    void listen('jarvis://hotkey', () => { void backend.hotkeyPressed(); void backend.voiceListen(); }).then((unlisten) => { off = unlisten; });
    return () => off?.();
  }, [backend]);

  useEffect(() => {
    const close = () => { if (overlay) closeOverlay(); };
    window.addEventListener('jarvis:command-sent', close);
    return () => window.removeEventListener('jarvis:command-sent', close);
  }, [closeOverlay, overlay]);

  useEffect(() => {
    if (!firstLaunch || overlay) return;
    const timer = window.setTimeout(() => append({ id: 'ritual-hello', role: 'jarvis', text: 'Привет.\n\nЯ JARVIS.\n\nА ты кто?', timestamp: Date.now() }), 1000);
    return () => window.clearTimeout(timer);
  }, [append, firstLaunch, overlay]);

  const send = useCallback((text: string) => {
    // Overlay is input-only: close it before touching the backend. TTS and
    // the MainWindow remain available through the normal WS event stream.
    if (overlay) closeOverlay();
    tts.interrupt(); void backend.interrupt(); append({ id: `user-${Date.now()}`, role: 'user', text, timestamp: Date.now() });
    if (firstLaunch) {
      void backend.saveFirstLaunchName(text); setFirstLaunch(false); transition('thinking');
      window.setTimeout(() => { append({ id: 'ritual-known', role: 'jarvis', text: `${text}.\n\nЗапомнил.\n\nДавай знакомиться.`, timestamp: Date.now() }); transition('idle'); }, 600);
      return;
    }
    transition('thinking'); void backend.sendCommand(text, []);
  }, [append, backend, closeOverlay, firstLaunch, overlay, transition, tts]);

  if (overlay) return <div className="overlayRoot"><InputOverlay onSend={send} onClose={closeOverlay} /></div>;
  return <><TrayIcon onHotkey={() => { void backend.hotkeyPressed(); void backend.voiceListen(); }} state={state} /><MainWindow messages={messages} state={state} onSend={send} firstLaunch={firstLaunch} /></>;
}

export default App;
