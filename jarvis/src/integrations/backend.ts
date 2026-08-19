/**
 * J.A.R.V.I.S. v4.0 — Backend Integration Adapter
 * Clean contract between the Oracle UI and the (existing) backend.
 *
 * The real backend already exists; this file defines the interface it must
 * satisfy. The mock adapter is intentionally gated behind VISUAL_PREVIEW and
 * is never selected by a production build.
 */

import type {
  ActivityEvent,
  AttachedFile,
  BackendAdapter,
  BackendEvent,
  EntityState,
  VitalsData,
} from '@/types';
import {
  WebSocketBackend,
  type CloudSettings,
  type CloudSettingsPatch,
} from './wsBackend';

export interface BackendRuntimeAdapter extends BackendAdapter {
  isConnected(): boolean;
  subscribeToConnection(listener: (connected: boolean) => void): () => void;
  getCloudSettings(): Promise<CloudSettings>;
  updateCloudSettings(patch: CloudSettingsPatch): Promise<CloudSettings>;
}

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
export function createMockBackend(): BackendRuntimeAdapter {
  const listeners = new Set<Listener>();
  const connectionListeners = new Set<(connected: boolean) => void>();
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
      content: 'Local runtime initialized · ready for commands',
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
  let cloud: CloudSettings = {
    provider: 'local',
    base_url: 'localhost',
    model: 'local-runtime',
    has_api_key: false,
    api_key_masked: '',
  };

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
              emit({ type: 'event:jarvis:end', payload: { id, content: full, tokens: 64, durationMs: 1200, model: 'local-runtime' } as unknown as ActivityEvent, timestamp: Date.now() });
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

    isConnected(): boolean {
      return true;
    },

    subscribeToConnection(cb: (connected: boolean) => void): () => void {
      connectionListeners.add(cb);
      cb(true);
      return () => connectionListeners.delete(cb);
    },

    getCloudSettings(): Promise<CloudSettings> {
      return Promise.resolve({ ...cloud });
    },

    updateCloudSettings(patch: CloudSettingsPatch): Promise<CloudSettings> {
      cloud = {
        ...cloud,
        ...(patch.provider !== undefined ? { provider: patch.provider } : {}),
        ...(patch.base_url !== undefined ? { base_url: patch.base_url } : {}),
        ...(patch.model !== undefined ? { model: patch.model } : {}),
        ...(patch.clear_api_key ? { has_api_key: false, api_key_masked: '' } :
          patch.api_key ? { has_api_key: true, api_key_masked: `••••${patch.api_key.slice(-4)}` } : {}),
      };
      return Promise.resolve({ ...cloud });
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
 */
export function createRealBackend(): WebSocketBackend {
  return new WebSocketBackend(WS_ENDPOINT);
}

/** Runtime selector. Mock data is an explicit visual-preview opt-in only. */
export function createBackend(): BackendRuntimeAdapter {
  const visualPreview = typeof import.meta !== 'undefined'
    && import.meta.env?.VITE_VISUAL_PREVIEW === '1';
  return visualPreview ? createMockBackend() : createRealBackend();
}
