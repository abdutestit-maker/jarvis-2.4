/**
 * J.A.R.V.I.S. v3.0 — Backend Bridge Hook
 *
 * Точка интеграции frontend ↔ backend.
 * Сейчас использует MOCK-адаптер (src/integrations/backend.ts) для визуального
 * preview. Чтобы подключить реальный backend — замените `createMockBackend()`
 * на `createRealBackend()` и реализуйте транспорт внутри него
 * (Tauri events / WebSocket / IPC). UI-логика не меняется.
 */

import { useCallback, useEffect, useRef } from 'react';
import { useUIState } from '@/hooks/useUIState';
import { useSessions } from '@/stores/sessionStore';
import {
  createRealBackend,
  TRANSPORT_STATE_MAP,
} from '@/integrations/backend';
import type {
  ActivityEvent, AttachedFile, EntityState, BackendAdapter, VitalsData,
} from '@/types';

// ===== CONNECT BACKEND HERE =====
// Live transport (Tauri event bus) is now wired inside createRealBackend();
// it falls back to the mock adapter automatically outside Tauri (vite dev).
const backend: BackendAdapter = createRealBackend();

// Single source of truth for transport -> entity state (kept in backend.ts).
const STATE_MAP: Record<string, EntityState> = TRANSPORT_STATE_MAP;

export function useBackendBridge() {
  const { dispatch } = useUIState();
  const { appendEvent, updateEvent } = useSessions();
  // Refs so the subscription effect never re-subscribes on session changes.
  const appendRef = useRef(appendEvent);
  const updateRef = useRef(updateEvent);
  appendRef.current = appendEvent;
  updateRef.current = updateEvent;

  const streamingId = useRef<string | null>(null);

  useEffect(() => {
    const unsub = backend.subscribeToEvents((e) => {
      // Смена состояния сущности
      if (e.type.startsWith('state:')) {
        const next = STATE_MAP[e.type];
        if (next) dispatch({ type: 'SET_ENTITY_STATE', payload: next });
        return;
      }

      // Vitals — kept in UI state only (no permanent CPU/RAM dashboard rendered)
      if (e.type === 'vitals:update') {
        dispatch({ type: 'UPDATE_VITALS', payload: e.payload as Partial<VitalsData> });
        return;
      }

      // Timeline events live per-session in the session store.
      if (e.type === 'event:seed' || e.type === 'event:command') {
        appendRef.current(e.payload as ActivityEvent);
        return;
      }

      // J.A.R.V.I.S. streaming
      if (e.type === 'event:jarvis:start') {
        const ev = e.payload as ActivityEvent;
        streamingId.current = ev.id;
        dispatch({ type: 'SET_STREAMING_MESSAGE', payload: ev.id });
        appendRef.current({ ...ev, kind: 'jarvis', content: '' });
        return;
      }
      if (e.type === 'event:jarvis:token') {
        const { id, token } = e.payload as { id: string; token: string };
        updateRef.current(id, { content: token });
        return;
      }
      if (e.type === 'event:jarvis:end') {
        const ev = e.payload as ActivityEvent;
        streamingId.current = null;
        dispatch({ type: 'SET_STREAMING_MESSAGE', payload: null });
        updateRef.current(ev.id, ev);
        return;
      }

      // Любые другие события активности
      if (e.type.startsWith('event:')) {
        appendRef.current(e.payload as ActivityEvent);
      }
    });

    // Стартовые vitals
    backend.getSystemVitals().then((v) => dispatch({ type: 'UPDATE_VITALS', payload: v }));

    return () => unsub();
  }, [dispatch]);

  const sendCommand = useCallback(async (text: string, files: AttachedFile[]) => {
    dispatch({ type: 'SET_ENTITY_STATE', payload: 'thinking' });
    await backend.sendCommand(text, files);
  }, [dispatch]);

  const interrupt = useCallback(async () => {
    await backend.interrupt();
  }, []);

  return { sendCommand, interrupt, isConnected: true };
}
