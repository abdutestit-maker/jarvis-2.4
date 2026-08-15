/**
 * J.A.R.V.I.S. v3.0 — Entry Point
 * Bootstrap React app with providers
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { MotionConfig } from 'framer-motion';
import App from './App';
import { UIStateProvider } from '@/hooks/useUIState';
import { ThemeProvider, useTheme } from '@/stores/themeStore';
import { SessionProvider } from '@/stores/sessionStore';
import './styles/tokens.css';
import './styles/globals.css';
import './styles/themes.css';
import './styles/glass.css';

/** Gates framer-motion JS animations on the effective reduce-motion setting. */
function MotionGate({ children }: { children: React.ReactNode }) {
  const { reduceMotion } = useTheme();
  return (
    <MotionConfig reducedMotion={reduceMotion ? 'always' : 'never'}>
      {children}
    </MotionConfig>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <UIStateProvider>
      <ThemeProvider>
        <MotionGate>
          <SessionProvider>
            <App />
          </SessionProvider>
        </MotionGate>
      </ThemeProvider>
    </UIStateProvider>
  </StrictMode>
);