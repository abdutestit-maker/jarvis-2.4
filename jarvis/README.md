# J.A.R.V.I.S. v3.0 — Oracle Interface

Frameless transparent desktop "Oracle" UI for an autonomous PC entity. Dark glassmorphism shell, subtle Hermes marble bust watermark with breathing cyan/gold rim light, glass message cards (not bubbles), thought-stream panel, sliding workspace, vitals, disabled mic.

## Stack

- **Tauri 2** (Rust backend, transparent window, Acrylic/Mica/Vibrancy)
- **React 18 + TypeScript** (strict mode)
- **Vite** (dev server, fast HMR)
- **Framer Motion** (animations)
- **Lucide React** (icons)
- **date-fns** (time formatting)

## Design Tokens (Locked)

```css
--bg-app: rgba(8, 8, 14, 0.75)
--bg-card: rgba(14, 14, 22, 0.50)
--bg-panel: rgba(10, 10, 16, 0.85)
--accent-cyan: #22D3EE
--accent-gold: #D9A959
--accent-green: #4ADE80
--accent-red: #F87171
```

## UI Zones

| Zone | Purpose |
|------|---------|
| TitleBar | Drag region, traffic lights, J.A.R.V.I.S. wordmark, state dot |
| Activity Stream | Glass cards: user (gold), jarvis (cyan), action (green) |
| Thought Panel | Collapsible: plan → tools → reasoning → self-corrections |
| Command Input | Frosted field, drag-drop files, Shift+Enter newline |
| Workspace Drawer | Right sliding panel: Files/Code/Preview/Data/Logs |
| Vitals | Top-right mono: CPU, RAM, Model, Ext API, Uptime |
| Background | Hermes statue (opacity 0.08-0.12) + breathing rim light |

## Quick Start

```bash
# 1. Install deps
cd jarvis
npm install

# 2. Install Rust (if not present)
# https://rustup.rs/

# 3. Run dev (frontend + Tauri)
npm run tauri:dev

# 4. Build for production
npm run tauri:build
```

## Project Structure

```
jarvis/
├── src/
│   ├── components/
│   │   ├── TitleBar.tsx
│   │   ├── ActivityStream/
│   │   │   ├── ActivityStream.tsx
│   │   │   ├── MessageCard.tsx
│   │   │   └── ThoughtPanel.tsx
│   │   ├── CommandInput.tsx
│   │   ├── WorkspaceDrawer.tsx
│   │   ├── Vitals.tsx
│   │   └── Background/
│   │       ├── HermesStatue.tsx
│   │       └── RimLight.tsx
│   ├── hooks/
│   │   ├── useUIState.ts
│   │   ├── useBackendBridge.ts
│   │   └── useStreamingText.ts
│   ├── state/
│   │   └── uiStateMachine.ts
│   ├── styles/
│   │   ├── tokens.css
│   │   ├── globals.css
│   │   └── glass.css
│   ├── types/
│   │   └── index.ts
│   ├── App.tsx
│   └── main.tsx
├── src-tauri/
│   ├── tauri.conf.json
│   ├── Cargo.toml
│   └── src/
│       ├── main.rs
│       └── window_effects.rs
├── public/
│   └── assets/
│       └── hermes-statue.png (placeholder)
├── package.json
├── tsconfig.json
├── vite.config.ts
└── index.html
```

## Entity States

```typescript
type EntityState =
  | 'idle'        // Waiting
  | 'listening'   // Voice input (v3.1+)
  | 'thinking'    // Processing, faster rim breathe
  | 'executing'   // Running tools
  | 'streaming'   // Streaming tokens
  | 'error'       // Error state
  | 'cloud';      // External API fallback
```

Valid transitions enforced in `uiStateMachine.ts`.

## Backend Integration

The frontend is **backend-agnostic**. Connect your existing Python/Rust backend via:

1. **Tauri Commands** (`src-tauri/src/main.rs`):
   ```rust
   #[tauri::command]
   async fn backend_send_message(text: String, files: Vec<String>) { ... }
   
   #[tauri::command]
   async fn backend_interrupt() { ... }
   ```

2. **Tauri Events** (backend → frontend):
   ```rust
   app.emit("backend:message:jarvis:token", json!({ "messageId": id, "token": "..." }))?;
   app.emit("backend:tool:start", json!({ "name": "read_file", "args": {...} }))?;
   app.emit("backend:vitals:update", json!({ "cpu": 12.5, "ram": 45.2, ... }))?;
   ```

3. **Frontend Bridge** (`src/hooks/useBackendBridge.ts`):
   - Already wired to listen for all events
   - Replace `// CONNECT BACKEND HERE` comments with actual dispatch logic
   - Exposes `sendMessage()`, `interrupt()`, `requestVitals()`

## Window Effects

| OS | Effect | Implementation |
|----|--------|----------------|
| Windows 11 | Acrylic | `window-vibrancy` crate (`apply_acrylic`), Mica fallback |
| Windows 10 | Mica | Fallback in `window_effects.rs` |
| macOS | Vibrancy | Native `apply_vibrancy` |
| Linux | Blur | `apply_blur` (KWin/GTK blur hints) |

Supported via the [`window-vibrancy`](https://crates.io/crates/window-vibrancy) crate (Tauri 2).
Configured in `src-tauri/tauri.conf.json`:
```json
{
  "app": {
    "windows": [{
      "transparent": true,
      "decorations": false,
      "titleBarStyle": "Transparent"
    }]
  }
}
```

## Fonts

- **Inter** — UI text
- **JetBrains Mono** — Code, mono, vitals
- **Cormorant Garamond** — Display, wordmark

Loaded via Google Fonts in `index.html`.

## Accessibility

- Semantic HTML (`<header>`, `<main>`, `<aside>`, `<article>`)
- ARIA labels on all interactive elements
- Focus visible states
- Reduced motion support (`prefers-reduced-motion`)
- Color contrast passes WCAG AA on glass cards

## Placeholder Asset

`public/assets/hermes-statue.png` — Replace with your marble bust image (curly-haired Greek god, classical). Recommended: 1024x1024+, transparent background.

## Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Vite dev server only |
| `npm run tauri:dev` | Full Tauri dev (frontend + Rust) |
| `npm run build` | TypeScript + Vite build |
| `npm run tauri:build` | Production bundle (MSIX/.dmg/.AppImage) |
| `npm run preview` | Preview Vite build |

## License

MIT — J.A.R.V.I.S. Project