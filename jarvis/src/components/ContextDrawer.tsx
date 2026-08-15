/**
 * J.A.R.V.I.S. v3.0 — Context Drawer
 * Optional right panel. Stays CLOSED when there is nothing real to show.
 * Surfaces REAL execution data derived from the event stream:
 *   - TASK progress (steps) under Execution
 *   - tool/action events under Sources/Files-like structure (real labels)
 *   - technical code under Details
 * No fabricated information. Collapses automatically when the stream is empty.
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight, ListChecks, Wrench, Terminal, FileText, Activity,
} from 'lucide-react';
import { useUIState } from '@/hooks/useUIState';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import type { ActivityEvent, WorkspaceTab } from '@/types';
import styles from './ContextDrawer.module.css';

const TABS: { id: WorkspaceTab; label: string; icon: typeof FileText }[] = [
  { id: 'execution', label: 'Выполнение', icon: ListChecks },
  { id: 'sources', label: 'Источники', icon: FileText },
  { id: 'details', label: 'Детали', icon: Terminal },
  { id: 'data', label: 'Данные', icon: Activity },
];

interface Props { events: ActivityEvent[]; }

export function ContextDrawer({ events }: Props) {
  const { isDrawerOpen, dispatch } = useUIState();
  const [tab, setTab] = useState<WorkspaceTab>('execution');

  const close = () => dispatch({ type: 'SET_DRAWER_OPEN', payload: false });
  const panelRef = useFocusTrap<HTMLElement>(isDrawerOpen, { onEscape: close, scrollLock: false, trap: false });

  const hasContent = useMemo(() => {
    return events.some((e) =>
      e.kind === 'progress' || e.kind === 'action' || e.kind === 'tool' ||
      e.kind === 'result' || e.kind === 'system' || e.detail || e.code
    );
  }, [events]);

  // Auto-close when there is nothing real to show.
  const open = isDrawerOpen && hasContent;

  const progress = events.filter((e) => e.kind === 'progress');
  const tools = events.filter((e) => e.kind === 'action' || e.kind === 'tool');
  const details = events.filter((e) => e.detail || e.code);
  const data = events.filter((e) => e.kind === 'result');

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          ref={panelRef}
          key="drawer"
          initial={{ x: '100%', opacity: 0.4 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: '100%', opacity: 0.4 }}
          transition={{ type: 'spring', damping: 28, stiffness: 280 }}
          role="complementary"
          aria-label="Контекст"
        >
          <header className={styles.header}>
            <span className={styles.title}>КОНТЕКСТ</span>
            <button className={styles.closeBtn} onClick={close} aria-label="Свернуть">
              <ChevronRight size={18} aria-hidden="true" />
            </button>
          </header>

          <nav className={styles.tabs} role="tablist" aria-label="Вкладки контекста">
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                className={`${styles.tab} ${tab === t.id ? styles.tabActive : ''}`}
                onClick={() => setTab(t.id)}
              >
                <t.icon size={15} />
                <span>{t.label}</span>
              </button>
            ))}
          </nav>

          <div className={styles.content} role="tabpanel">
            {tab === 'execution' && (
              <div className={styles.section}>
                {progress.length === 0 && <Empty text="Нет активных операций" />}
                {progress.map((ev) => (
                  <div key={ev.id} className={styles.card}>
                    <div className={styles.cardHead}>{ev.label ?? 'TASK'}</div>
                    <div className={styles.steps}>
                      {(ev.steps ?? []).map((s, i) => (
                        <div key={i} className={`${styles.step} ${stepCls(s.status)}`}>
                          <span className={styles.dot} /> {s.label}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tab === 'sources' && (
              <div className={styles.section}>
                {tools.length === 0 && <Empty text="Источники появятся при выполнении" />}
                {tools.map((ev) => (
                  <div key={ev.id} className={styles.card}>
                    <div className={styles.cardHead}>
                      <Wrench size={13} /> {ev.label ?? ev.kind}
                      <span className={styles.badge}>{ev.status ?? 'ok'}</span>
                    </div>
                    <div className={styles.cardBody}>{ev.content}</div>
                  </div>
                ))}
              </div>
            )}

            {tab === 'details' && (
              <div className={styles.section}>
                {details.length === 0 && <Empty text="Технические данные отсутствуют" />}
                {details.map((ev) => (
                  <div key={ev.id} className={styles.card}>
                    <div className={styles.cardHead}>{ev.label ?? ev.kind}</div>
                    {ev.detail && <div className={styles.cardBody}>{ev.detail}</div>}
                    {ev.code && (
                      <pre className={styles.code}>{ev.code}</pre>
                    )}
                  </div>
                ))}
              </div>
            )}

            {tab === 'data' && (
              <div className={styles.section}>
                {data.length === 0 && <Empty text="Структурированные данные отсутствуют" />}
                {data.map((ev) => (
                  <div key={ev.id} className={styles.card}>
                    <div className={styles.cardHead}>{ev.label ?? 'RESULT'}</div>
                    <div className={styles.cardBody}>{ev.content}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function Empty({ text }: { text: string }) {
  return <div className={styles.empty}>{text}</div>;
}

function stepCls(status?: string) {
  if (status === 'completed') return styles.stepDone;
  if (status === 'running') return styles.stepRun;
  if (status === 'failed') return styles.stepFail;
  return styles.stepPend;
}
