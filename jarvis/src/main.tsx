/**
 * J.A.R.V.I.S. v3.0 — Entry Point
 * Bootstrap React app with providers
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { ThemeProvider } from '@/stores/themeStore';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>
);
