import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { listen } from '@tauri-apps/api/event';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { StateMachine, presenceFromTransport, type PresenceState } from '@/bridge/StateMachine';
import { TTSController } from '@/bridge/TTSController';
import { OperatorShell } from '@/operator/OperatorShell';
import {
  confirmationFromEvent, createMission, fixtureMission, reduceMission,
  type OperatorMission, type UiMode,
} from '@/operator/model';
import { InputOverlay } from '@/overlay/InputOverlay';
import { TrayIcon } from '@/presence/TrayIcon';
import { WebSocketBackend } from '@/integrations/wsBackend';
import type { BackendEvent, PendingConfirmation } from '@/types';
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

// The command centre is for real operator work, not every conversational
// exchange. A greeting or "как дела?" must stay a calm dialogue without an
// artificial RESEARCH card; the backend still receives every command.
function needsMission(command: string): boolean {
  const text = command.trim().toLocaleLowerCase('ru-RU');
  if (!text) return false;
  return /\b(установ|настрой|настро|открой|запусти|закрой|скачай|найди|создай|сделай|удали|скопируй|перемести|поставь|включи|выключи|громк|музык|файл|папк|браузер|программ|приложен|проверь|настрой)\w*/u.test(text)
    || /\b(install|configure|open|launch|download|find|create|delete|copy|move|setup|check)\b/i.test(text);
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
  const [firstLaunch, setFirstLaunch] = useState(false);
  const [mode, setMode] = useState<UiMode>(() => initialMode(fixture));
  const [mission, setMission] = useState<OperatorMission | null>(() => fixture ? fixtureMission(fixture === 'verified' ? 'verified' : fixture === 'verify' ? 'verify' : 'download') : null);
  const [confirmation, setConfirmation] = useState<PendingConfirmation | null>(() => fixture === 'verify' ? { id: 'fixture-confirmation', prompt: 'Разрешить установку приложения?', tool: 'software.install', risk: { level: 'low' } } : null);
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
      if (event.type === 'profile:status') {
        setFirstLaunch(!(event.payload as { hasName: boolean }).hasName);
        return;
      }
      if (event.type === 'confirmation:required') {
        setConfirmation(confirmationFromEvent(event));
        setMission((current) => current ? reduceMission(current, event) : current);
        return;
      }
      if (event.type === 'event:voice_input') {
        const payload = event.payload as { text: string; confidence: number };
        if (payload.confidence >= 0.7 && payload.text.trim()) {
          append({ id: `voice-${Date.now()}`, role: 'user', text: payload.text, timestamp: Date.now() });
          if (needsMission(payload.text)) setMission(createMission(payload.text));
          transition('thinking');
          void backend.sendCommand(payload.text, []).catch(() => transition('error'));
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
    let off: (() => void) | undefined;
    void listen('jarvis://hotkey', () => { void backend.hotkeyPressed(); void backend.voiceListen(); }).then((unlisten) => { off = unlisten; });
    return () => off?.();
  }, [backend, fixture]);

  useEffect(() => {
    const close = () => { if (overlay) closeOverlay(); };
    window.addEventListener('jarvis:command-sent', close);
    return () => window.removeEventListener('jarvis:command-sent', close);
  }, [closeOverlay, overlay]);

  useEffect(() => {
    if (!firstLaunch || overlay || fixture) return;
    const timer = window.setTimeout(() => append({ id: 'ritual-hello', role: 'jarvis', text: 'Привет.\n\nЯ JARVIS.\n\nА ты кто?', timestamp: Date.now() }), 1000);
    return () => window.clearTimeout(timer);
  }, [append, firstLaunch, fixture, overlay]);

  const send = useCallback((text: string) => {
    if (overlay) closeOverlay();
    tts.interrupt();
    if (!fixture) void backend.interrupt().catch(() => undefined);
    append({ id: `user-${Date.now()}`, role: 'user', text, timestamp: Date.now() });
    if (firstLaunch) {
      if (!fixture) void backend.saveFirstLaunchName(text).catch(() => transition('error'));
      setFirstLaunch(false);
      transition('thinking');
      window.setTimeout(() => { append({ id: 'ritual-known', role: 'jarvis', text: `${text}.\n\nЗапомнил.\n\nДавай знакомиться.`, timestamp: Date.now() }); transition('idle'); }, 600);
      return;
    }
    if (needsMission(text)) setMission(createMission(text));
    setConfirmation(null);
    transition('thinking');
    if (!fixture) void backend.sendCommand(text, []).catch(() => transition('error'));
  }, [append, backend, closeOverlay, firstLaunch, fixture, overlay, transition, tts]);

  const answerConfirmation = useCallback((approved: boolean) => {
    const pending = confirmation;
    if (!pending) return;
    setConfirmation(null);
    if (!fixture) void backend.answerConfirmation(pending.id, approved).catch(() => transition('error'));
    if (approved) {
      const event: BackendEvent = { type: 'state:executing', payload: null, timestamp: Date.now() };
      setMission((current) => current ? reduceMission(current, event) : current);
      transition('thinking');
    }
  }, [backend, confirmation, fixture, transition]);

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
    setConfirmation(null);
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
      confirmation={confirmation}
      firstLaunch={firstLaunch}
      onModeChange={updateMode}
      onSend={send}
      onInterrupt={interrupt}
      onVoiceListen={voiceListen}
      onConfirm={answerConfirmation}
      onNewSession={newSession}
    />
  </>;
}

export default App;
