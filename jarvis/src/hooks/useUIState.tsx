/**
 * J.A.R.V.I.S. v3.0 — UI State Hook
 * React context + reducer for global UI state
 */

import { createContext, useContext, useReducer, useMemo, type ReactNode, type Dispatch } from 'react';
import { uiReducer, initialUIState, selectors, type UIAction } from '@/state/uiStateMachine';
import type { UIState } from '@/types';

const UIStateContext = createContext<{
  state: UIState;
  dispatch: Dispatch<UIAction>;
  selectors: typeof selectors;
} | null>(null);

export function UIStateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(uiReducer, initialUIState);

  const value = useMemo(() => ({ state, dispatch, selectors }), [state]);

  return (
    <UIStateContext.Provider value={value}>
      {children}
    </UIStateContext.Provider>
  );
}

export function useUIState() {
  const context = useContext(UIStateContext);
  if (!context) {
    throw new Error('useUIState must be used within UIStateProvider');
  }
  return { ...context.state, dispatch: context.dispatch, selectors: context.selectors };
}