/**
 * J.A.R.V.I.S. v3.0 — Backend Integration Adapter
 * Clean contract between the Oracle UI and the (existing) backend.
 *
 * The real backend already exists; this file defines the interface it must
 * satisfy and ships a MOCK adapter used ONLY for visual preview.
 * Replace `createMockBackend()` with `createRealBackend()` once the live
 * transport (Tauri events / WebSocket / IPC) is wired.
 */

import type {
  ActivityEvent,
  AttachedFile,
  BackendAdapter,
  BackendEvent,
  EntityState,
  VitalsData,
} from '@/types';
import { WebSocketBackend } from './wsBackend';

/* ===== Event emitter for the mock ===== */
type Listener = (e: BackendEvent) => void;

const STATE_LABEL: Record<EntityState, string> = {
  idle: 'ONLINE',
  listening: 'LISTENING',
  thinking: 'THINKING',
  executing: 'EXECUTING',
  streaming: 'STREAMING',
  error: 'ERROR',
  cloud: 'CLOUD',
};

/**
 * MOCK backend — generates a believable operational timeline so the UI can be
 * visually verified without the real agent loop. Not for production.
 */
export function createMockBackend(): BackendAdapter {
  const listeners = new Set<Listener>();
  const emit = (e: BackendEvent) => listeners.forEach((l) => l(e));
  const emitState = (s: EntityState) =>
    emit({ type: `state:${s}` as unknown as BackendEvent['type'], payload: null, timestamp: Date.now() });

  let counter = 0;
  const uid = (p: string) => `${p}-${Date.now()}-${counter++}`;

  // A small scripted scenario used to populate the initial timeline.
  const seed: ActivityEvent[] = [
    {
      id: uid('sys'),
      kind: 'system',
      timestamp: Date.now() - 240000,
      content: 'Oracle interface initialized · local model QWEN3-4B online',
    },
    {
      id: uid('cmd'),
      kind: 'command',
      timestamp: Date.now() - 180000,
      content: 'Analyze the Jarvis project structure and report the architecture.',
    },
    {
      id: uid('an'),
      kind: 'analysis',
      timestamp: Date.now() - 175000,
      content: 'Decomposing request · mapping repository, tools and memory layers.',
    },
    {
      id: uid('act'),
      kind: 'action',
      timestamp: Date.now() - 168000,
      label: 'FILE SYSTEM',
      status: 'completed',
      content: '127 files discovered across 14 modules',
      detail: '127 files discovered across 14 modules',
      code: '$ find ./jarvis -type f | wc -l\n127',
    },
    {
      id: uid('act2'),
      kind: 'action',
      timestamp: Date.now() - 160000,
      label: 'SEARCH',
      status: 'completed',
      content: 'Indexed project documentation',
      detail: 'Indexed project documentation',
      code: 'grep -r "architecture" docs/  → 9 matches',
    },
    {
      id: uid('res'),
      kind: 'result',
      timestamp: Date.now() - 150000,
      label: 'ANALYSIS',
      content: 'Architecture survey complete · 4 subsystems identified (models, tools, memory, orchestration).',
    },
  ];

  let started = false;

  return {
    sendCommand(text: string, files: AttachedFile[]): Promise<void> {
      return new Promise((resolve) => {
        emitState('thinking');

        emit({ type: 'event:command', payload: { id: uid('cmd'), content: text, files } as unknown as ActivityEvent, timestamp: Date.now() });
        emit({ type: 'event:analysis', payload: { id: uid('an'), content: 'Interpreting objective · planning operations.' } as unknown as ActivityEvent, timestamp: Date.now() });

        setTimeout(() => {
          emitState('executing');
          emit({
            type: 'event:progress',
            payload: {
              id: uid('prog'),
              kind: 'progress',
              label: 'TASK',
              content: '4 operations',
              steps: [
                { label: 'Planning', status: 'completed' },
                { label: 'Search', status: 'running' },
                { label: 'Analysis', status: 'pending' },
                { label: 'Verification', status: 'pending' },
              ],
            } as unknown as ActivityEvent,
            timestamp: Date.now(),
          });
        }, 600);

        setTimeout(() => {
          emit({
            type: 'event:action',
            payload: { id: uid('act'), kind: 'action', label: 'SHELL', status: 'completed', detail: 'Executed probe command', code: '$ uname -a\nLinux jarvis-host 6.1.0' } as unknown as ActivityEvent,
            timestamp: Date.now(),
          });
        }, 1300);

        setTimeout(() => {
          emitState('streaming');
          const id = uid('jar');
          emit({ type: 'event:jarvis:start', payload: { id } as unknown as ActivityEvent, timestamp: Date.now() });
          const full =
            'Understood. I have surveyed the local environment and identified the operational surface. ' +
            'The system is stable, the model is resident, and I am ready to act on your directive. ' +
            'What is our next objective?';
          let i = 0;
          const tick = setInterval(() => {
            i += 3;
            emit({ type: 'event:jarvis:token', payload: { id, token: full.slice(0, i) }, timestamp: Date.now() });
            if (i >= full.length) {
              clearInterval(tick);
              emit({ type: 'event:jarvis:end', payload: { id, content: full, tokens: 64, durationMs: 1200, model: 'qwen3-4b-local' } as unknown as ActivityEvent, timestamp: Date.now() });
              emitState('idle');
              resolve();
            }
          }, 35);
        }, 2000);
      });
    },

    subscribeToEvents(cb: Listener): () => void {
      listeners.add(cb);
      if (!started) {
        started = true;
        // Push seed timeline shortly after subscription.
        setTimeout(() => seed.forEach((e) => cb({ type: 'event:seed', payload: e, timestamp: e.timestamp } as unknown as BackendEvent)), 50);
      }
      return () => listeners.delete(cb);
    },

    getSystemVitals(): Promise<VitalsData> {
      return Promise.resolve({
        cpu: 8 + Math.random() * 30,
        ram: 30 + Math.random() * 40,
        modelStatus: 'local',
        externalApi: 'standby',
        uptime: Date.now(),
      });
    },

    interrupt(): Promise<void> {
      emitState('idle');
      return Promise.resolve();
    },

    answerConfirmation(): Promise<void> {
      // Mock: никаких ожидающих подтверждений нет.
      return Promise.resolve();
    },
  };
}

/* Expose the state label map for the TitleBar. */
export { STATE_LABEL };

/* ===== Status mapping (single source of truth) ===== */

/** Transport event channel -> UI entity state. Mirrors the bridge's STATE_MAP. */
export const TRANSPORT_STATE_MAP: Record<string, EntityState> = {
  'state:thinking': 'thinking',
  'state:executing': 'executing',
  'state:streaming': 'streaming',
  'state:idle': 'idle',
  'state:error': 'error',
  'state:cloud': 'cloud',
  'state:listening': 'listening',
};

const WS_ENDPOINT = 'ws://127.0.0.1:8771';

/**
 * Real adapter — binds to the live Python WebSocket core on localhost,
 * maps backend events onto the BackendAdapter contract, and exposes
 * cloud-provider settings (masked — never the raw API key).
 * Falls back to the mock adapter when a live WebSocket connection cannot be
 * established (e.g. vite preview without the Python core), so the UI stays
 * fully functional.
 */
export function createRealBackend(): WebSocketBackend {
  return new WebSocketBackend(WS_ENDPOINT);
}
