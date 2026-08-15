/**
 * J.A.R.V.I.S. v3.0 — UI State Machine
 * Pure, testable state transitions for the entity + surface toggles.
 */

import type { EntityState, UIState, VitalsData } from '@/types';

/* ===== Valid Transitions ===== */
const validTransitions: Record<EntityState, EntityState[]> = {
  idle: ['listening', 'thinking', 'cloud'],
  listening: ['thinking', 'idle', 'error'],
  thinking: ['executing', 'streaming', 'idle', 'error'],
  executing: ['streaming', 'thinking', 'idle', 'error'],
  streaming: ['idle', 'thinking', 'executing', 'error'],
  error: ['idle', 'thinking'],
  cloud: ['streaming', 'idle', 'error'],
};

/* ===== Initial State ===== */
const initialVitals: VitalsData = {
  cpu: 0,
  ram: 0,
  modelStatus: 'standby',
  externalApi: 'standby',
  uptime: 0,
};

export const initialUIState: UIState = {
  entityState: 'idle',
  isDrawerOpen: false,
  isEventExpanded: {},
  streamingEventId: null,
  vitals: initialVitals,
  windowEffect: 'acrylic',
  isSidebarOpen: true,
  isSettingsOpen: false,
};

/* ===== State Machine ===== */
export function uiReducer(state: UIState, action: UIAction): UIState {
  switch (action.type) {
    case 'SET_ENTITY_STATE': {
      const nextState = action.payload as EntityState;
      if (!validTransitions[state.entityState].includes(nextState)) {
        console.warn(
          `[StateMachine] Invalid transition: ${state.entityState} → ${nextState}`
        );
        return state;
      }
      return { ...state, entityState: nextState };
    }

    case 'TOGGLE_DRAWER':
      return { ...state, isDrawerOpen: !state.isDrawerOpen };

    case 'SET_DRAWER_OPEN':
      return { ...state, isDrawerOpen: action.payload as boolean };

    case 'TOGGLE_SIDEBAR':
      return { ...state, isSidebarOpen: !state.isSidebarOpen };

    case 'SET_SIDEBAR_OPEN':
      return { ...state, isSidebarOpen: action.payload as boolean };

    case 'SET_SETTINGS_OPEN':
      return { ...state, isSettingsOpen: action.payload as boolean };

    case 'TOGGLE_SETTINGS':
      return { ...state, isSettingsOpen: !state.isSettingsOpen };

    case 'TOGGLE_THOUGHT': {
      const eventId = action.payload as string;
      return {
        ...state,
        isEventExpanded: {
          ...state.isEventExpanded,
          [eventId]: !state.isEventExpanded[eventId],
        },
      };
    }

    case 'SET_STREAMING_MESSAGE':
      return { ...state, streamingEventId: action.payload as string | null };

    case 'UPDATE_VITALS': {
      const vitals = action.payload as Partial<VitalsData>;
      return { ...state, vitals: { ...state.vitals, ...vitals } };
    }

    case 'SET_WINDOW_EFFECT':
      return { ...state, windowEffect: action.payload as UIState['windowEffect'] };

    case 'RESET':
      return initialUIState;

    default:
      return state;
  }
}

/* ===== Action Types ===== */
export type UIAction =
  | { type: 'SET_ENTITY_STATE'; payload: EntityState }
  | { type: 'TOGGLE_DRAWER' }
  | { type: 'SET_DRAWER_OPEN'; payload: boolean }
  | { type: 'TOGGLE_SIDEBAR' }
  | { type: 'SET_SIDEBAR_OPEN'; payload: boolean }
  | { type: 'SET_SETTINGS_OPEN'; payload: boolean }
  | { type: 'TOGGLE_SETTINGS' }
  | { type: 'TOGGLE_THOUGHT'; payload: string }
  | { type: 'SET_STREAMING_MESSAGE'; payload: string | null }
  | { type: 'UPDATE_VITALS'; payload: Partial<VitalsData> }
  | { type: 'SET_WINDOW_EFFECT'; payload: UIState['windowEffect'] }
  | { type: 'RESET' };

/* ===== Selectors ===== */
export const selectors = {
  isBusy: (state: UIState) =>
    ['thinking', 'executing', 'streaming', 'cloud'].includes(state.entityState),

  isThinking: (state: UIState) => state.entityState === 'thinking' || state.entityState === 'executing',

  isStreaming: (state: UIState) => state.entityState === 'streaming',

  hasError: (state: UIState) => state.entityState === 'error',

  rimBreatheDuration: (state: UIState) =>
    state.entityState === 'thinking' ? 1800 : 4500,
};
