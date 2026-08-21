import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { StateMachine, presenceFromTransport, type PresenceState } from '@/bridge/StateMachine';
import { TTSController } from '@/bridge/TTSController';
import { OperatorShell } from '@/operator/OperatorShell';
import {
  fixtureMission, reduceMission,
  type OperatorMission, type UiMode,
} from '@/operator/model';
import { InputOverlay } from '@/overlay/InputOverlay';
import { TrayIcon } from '@/presence/TrayIcon';
import { WebSocketBackend } from '@/integrations/wsBackend';
import type { BackendEvent } from '@/types';
import type { PresenceMessage } from '@/window/MessageStream';
import './presence.css';

function isOverlayWindow(): boolean {
  try { return getCurrentWindow().label === 'overlay'; } catch { return false; }
}

function fixtureName(): string | null {
  if (!import.meta.env.DEV) return null;
  return new URLSearchParams(window.location.search).get('fixture');
}

function fixtureMessages(fixture: string | null): PresenceMessage[] {
  if (!fixture) return [];
  const now = Date.now();
  return [
    { id: 'fixture-user', role: 'user', text: 'Установи тестовую программу и настрой её.', timestamp: now - 32_000 },
    { id: 'fixture-jarvis', role: 'jarvis', text: fixture === 'verified' ? 'Готово. Проверяйте, сэр.' : 'Сейчас разберусь, сэр.', timestamp: now - 24_000 },
  ];
}


function initialMode(fixture: string | null): UiMode {
  if (fixture && fixture !== 'compact') return 'command_center';
  const saved = window.localStorage.getItem('jarvis.ui.mode');
  return saved === 'command_center' ? 'command_center' : 'presence';
}

function App() {
  const fixture = useMemo(fixtureName, []);
  const backend = useMemo(() => new WebSocketBackend('ws://127.0.0.1:8771'), []);
  const machine = useMemo(() => new StateMachine(), []);
  const tts = useMemo(() => new TTSController(), []);
  const [messages, setMessages] = useState<PresenceMessage[]>(() => fixtureMessages(fixture));
  const [state, setState] = useState<PresenceState>(fixture === 'verified' ? 'idle' : fixture ? 'thinking' : 'idle');
  const [mode, setMode] = useState<UiMode>(() => initialMode(fixture));
  const [mission, setMission] = useState<OperatorMission | null>(() => fixture ? fixtureMission(fixture === 'verified' ? 'verified' : fixture === 'verify' ? 'verify' : 'download') : null);
  const [connected, setConnected] = useState(() => Boolean(fixture) || backend.isConnected());
  const [runtimeState, setRuntimeState] = useState(() => fixture ? 'ready' : 'starting');
  const streaming = useRef<string | null>(null);
  const overlay = isOverlayWindow();

  const transition = useCallback((next: PresenceState) => setState(machine.transition(next)), [machine]);
  const append = useCallback((message: PresenceMessage) => setMessages((current) => [...current, message].slice(-30)), []);
  const closeOverlay = useCallback(() => { try { void getCurrentWindow().hide(); } catch { /* browser fixture */ } }, []);
  const updateMode = useCallback((next: UiMode) => { window.localStorage.setItem('jarvis.ui.mode', next); setMode(next); }, []);

  useEffect(() => {
    if (fixture) return;
    return backend.subscribeToEvents((event: BackendEvent) => {
      if (event.type.startsWith('state:')) {
        transition(presenceFromTransport(event.type.slice(6)));
        setMission((current) => current ? reduceMission(current, event) : current);
        return;
      }
      if (event.type === 'runtime:status') {
        const payload = event.payload as { state?: string; ready?: boolean };
        setRuntimeState(payload.ready ? 'ready' : (payload.state ?? 'starting'));
        setConnected(backend.isConnected());
        return;
      }
      if (event.type === 'confirmation:required') {
        // Autonomous mode: confirmations are backend audit events, never a UI gate.
        setMission((current) => current ? reduceMission(current, event) : current);
        return;
      }
  if (event.type === 'event:voice_input') {
  const payload = event.payload as { text: string; confidence: number };
  if (payload.confidence >= 0.7 && payload.text.trim()) {
  append({ id: `voice-${Date.now()}`, role: 'user', text: payload.text, timestamp: Date.now() });
  transition('thinking');
  }
  return;
  }

      if (event.type === 'event:jarvis:start') {
        const payload = event.payload as { id: string };
        streaming.current = payload.id;
        append({ id: payload.id, role: 'jarvis', text: '', timestamp: event.timestamp });
        transition('thinking');
        return;
      }
      if (event.type === 'event:jarvis:token' || event.type === 'event:jarvis:end') {
        const payload = event.payload as { id: string; content?: string; token?: string };
        const text = payload.content ?? payload.token ?? '';
        setMessages((current) => current.map((message) => message.id === (streaming.current ?? payload.id) ? { ...message, text } : message));
        if (event.type === 'event:jarvis:end') {
          streaming.current = null;
          tts.finish();
          transition('idle');
        }
        return;
      }
      if (event.type === 'event:action' || event.type === 'event:tool' || event.type === 'event:progress' || event.type === 'event:result' || event.type === 'event:system') {
        setMission((current) => current ? reduceMission(current, event) : current);
      }
    });
  }, [append, backend, fixture, transition, tts]);

  useEffect(() => {
    if (fixture) return;
    return backend.subscribeToConnection((value) => setConnected(value));
  }, [backend, fixture]);

  useEffect(() => {
    if (fixture) return;
    let off: (() => void) | undefined;
    void listen('jarvis://hotkey', () => { void backend.hotkeyPressed(); void backend.voiceListen(); }).then((unlisten) => { off = unlisten; });
    return () => off?.();
  }, [backend, fixture]);

  useEffect(() => {
    const close = () => { if (overlay) closeOverlay(); };
    window.addEventListener('jarvis:command-sent', close);
    return () => window.removeEventListener('jarvis:command-sent', close);
  }, [closeOverlay, overlay]);


  const send = useCallback((text: string) => {
    if (overlay) closeOverlay();
    tts.interrupt();
    if (!fixture) void backend.interrupt().catch(() => undefined);
    append({ id: `user-${Date.now()}`, role: 'user', text, timestamp: Date.now() });
    transition('thinking');
    if (!fixture) void backend.sendCommand(text, []).catch(() => transition('error'));
  }, [append, backend, closeOverlay, fixture, overlay, transition, tts]);

  const interrupt = useCallback(() => {
    tts.interrupt();
    if (!fixture) void backend.interrupt().catch(() => undefined);
    transition('idle');
  }, [backend, fixture, transition, tts]);

  const voiceListen = useCallback(() => {
    if (!fixture) void backend.voiceListen().catch(() => transition('error'));
  }, [backend, fixture, transition]);

  const newSession = useCallback(() => {
    setMessages([]);
    setMission(null);
    transition('idle');
  }, [transition]);

  if (overlay) return <div className="overlayRoot"><InputOverlay onSend={send} onClose={closeOverlay} /></div>;
  return <>
    <TrayIcon onHotkey={() => { void backend.hotkeyPressed(); void backend.voiceListen(); }} state={state} />
    <OperatorShell
      messages={messages}
      state={state}
      mode={mode}
      mission={mission}
      confirmation={null}
      onModeChange={updateMode}
      onSend={send}
      onInterrupt={interrupt}
      onVoiceListen={voiceListen}
      onConfirm={() => undefined}
      onNewSession={newSession}
      connected={connected}
      runtimeState={runtimeState}
    />
  </>;
}

export default App;
