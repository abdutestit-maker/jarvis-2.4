/**
 * J.A.R.V.I.S. v3.0 — Activity Stream
 * Operational timeline inside a calm, centered ~820px column.
 * Not chat bubbles: each event is a unified content surface.
 */

import { useRef, useEffect, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useUIState } from '@/hooks/useUIState';
import type { ActivityEvent } from '@/types';
import { ActivityEventCard } from './ActivityEventCard';
import styles from './ActivityStream.module.css';

interface Props {
  events: ActivityEvent[];
  onRetry?: () => void;
}

export function ActivityStream({ events, onRetry }: Props) {
  const { streamingEventId, entityState } = useUIState();
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
        <div className={styles.empty}>
          <span className={styles.emptyTitle}>SYSTEM STANDBY</span>
          <span className={styles.emptySub}>Ожидание директивы</span>
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
            <span className={`${styles.liveDot}`} /><span className={styles.liveText}>J.A.R.V.I.S. отвечает</span>
          </motion.div>
        )}
        {entityState === 'thinking' && (
          <motion.div className={styles.live} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <span className={`${styles.liveDot} ${styles.thinking}`} /><span className={styles.liveText}>Обработка</span>
          </motion.div>
        )}
        {entityState === 'executing' && (
          <motion.div className={styles.live} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <span className={`${styles.liveDot} ${styles.executing}`} /><span className={styles.liveText}>Выполнение операций</span>
          </motion.div>
        )}

        <div ref={endRef} />
      </div>
    </div>
  );
}
