/**
 * J.A.R.V.I.S. v3.0 — Activity Stream
 * Operational timeline inside a calm, centered ~820px column.
 * Not chat bubbles: each event is a unified content surface.
 */

import { useRef, useEffect, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useUIState } from '@/hooks/useUIState';
import { useTheme } from '@/stores/themeStore';
import { CoreSymbol } from '@/components/CoreSymbol/CoreSymbol';
import type { ActivityEvent } from '@/types';
import { ActivityEventCard } from './ActivityEventCard';
import styles from './ActivityStream.module.css';

interface Props {
  events: ActivityEvent[];
  onRetry?: () => void;
}

function greetingFor(date: Date): string {
  const h = date.getHours();
  if (h >= 5 && h < 12) return 'Доброе утро';
  if (h >= 12 && h < 18) return 'Добрый день';
  if (h >= 18 && h < 23) return 'Добрый вечер';
  return 'Доброй ночи';
}

export function ActivityStream({ events, onRetry }: Props) {
  const { streamingEventId, entityState } = useUIState();
  const { profile } = useTheme();
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const autoScroll = useRef(true);

  // The last jarvis event index (for the retry affordance).
  const lastJarvisId = (() => {
    for (let i = events.length - 1; i >= 0; i--) {
      if (events[i].kind === 'jarvis') return events[i].id;
    }
    return null;
  })();

  useEffect(() => {
    if (autoScroll.current && endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [events, streamingEventId]);

  const onScroll = useCallback(() => {
    const el = containerRef.current; if (!el) return;
    autoScroll.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  }, []);

  const who = profile?.name?.trim();

  return (
    <div
      ref={containerRef}
      className={styles.stream}
      onScroll={onScroll}
      role="log"
      aria-live="polite"
      aria-label="Лента активности J.A.R.V.I.S."
    >
      {events.length === 0 && (
        <div className={styles.welcome}>
          <motion.div
            className={styles.welcomeCore}
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          >
            <CoreSymbol state="idle" size={58} />
          </motion.div>
          <motion.h2
            className={styles.welcomeTitle}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            {greetingFor(new Date())}{who ? `, ${who}` : ''}.
          </motion.h2>
          <motion.p
            className={styles.welcomeSub}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.22, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            J.A.R.V.I.S. на связи — сформулируйте задачу, и я приступлю.
          </motion.p>
          <motion.div
            className={styles.welcomeHints}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.6 }}
          >
            <span><kbd>Ctrl</kbd>+<kbd>K</kbd> палитра команд</span>
            <span className={styles.welcomeDot} aria-hidden="true" />
            <span><kbd>F11</kbd> полноэкранный режим</span>
          </motion.div>
        </div>
      )}

      <div className={styles.column}>
        <AnimatePresence initial={false}>
          {events.map((ev) => (
            <ActivityEventCard
              key={ev.id}
              event={ev}
              isStreaming={ev.id === streamingEventId}
              isLastJarvis={ev.id === lastJarvisId && ev.kind === 'jarvis'}
              onRetry={onRetry}
            />
          ))}
        </AnimatePresence>

        {entityState === 'streaming' && (
          <motion.div className={styles.live} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <span className={styles.liveDot} /><span className={styles.liveText}>J.A.R.V.I.S. отвечает</span>
          </motion.div>
        )}
        {entityState === 'thinking' && (
          <motion.div className={styles.live} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <span className={styles.dots} aria-hidden="true"><span /><span /><span /></span>
            <span className={styles.liveText}>Анализирую запрос</span>
          </motion.div>
        )}
        {entityState === 'executing' && (
          <motion.div className={styles.live} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <span className={styles.liveDot} /><span className={styles.liveText}>Выполняю операции</span>
          </motion.div>
        )}

        <div ref={endRef} />
      </div>
    </div>
  );
}
