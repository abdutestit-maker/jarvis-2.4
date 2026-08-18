/**
 * J.A.R.V.I.S. v3.0 — Entry Point
 * Bootstrap React app with providers
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
