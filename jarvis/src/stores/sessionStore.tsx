/**
 * J.A.R.V.I.S. v3.0 — Session store (frontend-only, client-side).
 *
 * The existing backend bridge has no session system, so sessions are a
 * legitimate client-side organizational layer persisted to localStorage.
 * They are REAL: created/pinned/renamed/selected/deleted by the user, and
 * each session owns its own event timeline (eventsBySession). Switching
 * sessions actually swaps the rendered timeline — no fake affordance.
 *
 * With the mock backend a session is seeded on first mount; a real backend
 * would populate history per session id. Event counts are capped per
 * session (EVENT_CAP) so localStorage never blows its quota on long transcripts.
 */

import {
  createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode,
} from 'react';
import type { ActivityEvent, Session } from '@/types';

const KEY_SESSIONS = 'jarvis.sessions.v3';
const KEY_EVENTS = 'jarvis.sessions.events.v3';
const EVENT_CAP = 200;

/** Quota-safe persistence. On QuotaExceeded: prune oldest events per session, retry once. */
function safeSet(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    if (key === KEY_EVENTS) {
      try {
        const obj = JSON.parse(localStorage.getItem(key) || '{}') as Record<string, ActivityEvent[]>;
        for (const k of Object.keys(obj)) obj[k] = obj[k].slice(-Math.ceil(EVENT_CAP / 2));
        localStorage.setItem(key, JSON.stringify(obj));
      } catch { /* best effort */ }
    }
  }
}

function uid(): string {
  return `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

function freshSession(): Session {
  const now = Date.now();
  return {
    id: uid(),
    title: 'New session',
    pinned: false,
    createdAt: now,
    updatedAt: now,
    messageCount: 0,
  };
}

function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem(KEY_SESSIONS);
    if (raw) {
      const arr = JSON.parse(raw) as Session[];
      if (Array.isArray(arr) && arr.length) return arr;
    }
  } catch {
    /* ignore */
  }
  return [freshSession()];
}

function loadEvents(): Record<string, ActivityEvent[]> {
  try {
    const raw = localStorage.getItem(KEY_EVENTS);
    if (raw) {
      const obj = JSON.parse(raw) as Record<string, ActivityEvent[]>;
      if (obj && typeof obj === 'object') return obj;
    }
  } catch {
    /* ignore */
  }
  return {};
}

interface SessionContextValue {
  sessions: Session[];
  activeId: string | null;
  active: Session;
  /** Events belonging to the active session (reactive). */
  events: ActivityEvent[];
  newSession: () => void;
  select: (id: string) => void;
  togglePin: (id: string) => void;
  rename: (id: string, title: string) => void;
  remove: (id: string) => void;
  updateActive: (patch: Partial<Session>) => void;
  /** Append an event to the active session's timeline. */
  appendEvent: (ev: ActivityEvent) => void;
  /** Patch an existing event in the active session. */
  updateEvent: (id: string, patch: Partial<ActivityEvent>) => void;
}

const Ctx = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>(loadSessions);
  const [eventsBySession, setEventsBySession] = useState<Record<string, ActivityEvent[]>>(loadEvents);
  const [activeId, setActiveId] = useState<string | null>(null);

  // Refs so append/update never nest setState updaters.
  const activeIdRef = useRef<string | null>(activeId);
  const sessionsRef = useRef<Session[]>(sessions);
  const eventsBySessionRef = useRef<Record<string, ActivityEvent[]>>(eventsBySession);
  activeIdRef.current = activeId;
  sessionsRef.current = sessions;
  eventsBySessionRef.current = eventsBySession;

  // Ensure an active session exists.
  useEffect(() => {
    if (!activeId && sessions.length) setActiveId(sessions[0].id);
  }, [sessions, activeId]);

  // Persist sessions immediately (low-frequency writes).
  useEffect(() => { safeSet(KEY_SESSIONS, sessions); }, [sessions]);

  // Debounce event writes — streaming appends many tokens/sec; avoid main-thread thrash.
  const eventsTimer = useRef<number | null>(null);
  useEffect(() => {
    if (eventsTimer.current) window.clearTimeout(eventsTimer.current);
    eventsTimer.current = window.setTimeout(() => safeSet(KEY_EVENTS, eventsBySession), 400);
    return () => { if (eventsTimer.current) window.clearTimeout(eventsTimer.current); };
  }, [eventsBySession]);

  // Flush pending writes on tab hide / unload so nothing is lost mid-stream.
  useEffect(() => {
    const flush = () => {
      if (eventsTimer.current) window.clearTimeout(eventsTimer.current);
      safeSet(KEY_EVENTS, eventsBySessionRef.current);
    };
    const onVis = () => { if (document.visibilityState === 'hidden') flush(); };
    window.addEventListener('beforeunload', flush);
    document.addEventListener('visibilitychange', onVis);
    return () => {
      window.removeEventListener('beforeunload', flush);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({
      sessions,
      activeId,
      active: sessions.find((s) => s.id === activeId) ?? sessions[0],
      events: eventsBySession[activeId ?? ''] ?? [],

      newSession: () => {
        const s = freshSession();
        setSessions((prev) => [s, ...prev]);
        setActiveId(s.id);
      },
      select: (id) => setActiveId(id),
      togglePin: (id) =>
        setSessions((prev) =>
          prev.map((s) => (s.id === id ? { ...s, pinned: !s.pinned } : s))
        ),
      rename: (id, title) =>
        setSessions((prev) =>
          prev.map((s) => (s.id === id ? { ...s, title: title || s.title } : s))
        ),
      remove: (id) => {
        const next = sessions.filter((s) => s.id !== id);
        const remaining = next.length ? next : [freshSession()];
        setSessions(remaining);
        setActiveId(remaining[0].id);
        setEventsBySession((ev) => {
          const copy = { ...ev };
          delete copy[id];
          return copy;
        });
      },
      updateActive: (patch) =>
        setSessions((prev) =>
          prev.map((s) => (s.id === activeId ? { ...s, ...patch, updatedAt: Date.now() } : s))
        ),

      appendEvent: (ev) => {
        const target = activeIdRef.current ?? sessionsRef.current[0]?.id ?? null;
        if (!target) return;
        setEventsBySession((prev) => {
          const bucket = prev[target] ? [...prev[target]] : [];
          if (bucket.some((e) => e.id === ev.id)) return prev; // idempotent (StrictMode-safe)
          bucket.push(ev);
          if (bucket.length > EVENT_CAP) bucket.splice(0, bucket.length - EVENT_CAP);
          return { ...prev, [target]: bucket };
        });
        // Derive the session title from the first user command (real data).
        if (ev.kind === 'command') {
          setSessions((prev) =>
            prev.map((s) =>
              s.id === target && (s.title === 'New session' || !s.title)
                ? { ...s, title: ev.content.slice(0, 40) || s.title, updatedAt: Date.now() }
                : s
            )
          );
        }
        setSessions((prev) =>
          prev.map((s) =>
            s.id === target ? { ...s, messageCount: s.messageCount + 1, updatedAt: Date.now() } : s
          )
        );
      },

      updateEvent: (id, patch) => {
        const target = activeIdRef.current ?? sessionsRef.current[0]?.id ?? null;
        if (!target) return;
        setEventsBySession((prev) => {
          const bucket = prev[target];
          if (!bucket) return prev;
          return { ...prev, [target]: bucket.map((e) => (e.id === id ? { ...e, ...patch } : e)) };
        });
      },
    }),
    [sessions, eventsBySession, activeId]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSessions() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useSessions must be used within SessionProvider');
  return ctx;
}
