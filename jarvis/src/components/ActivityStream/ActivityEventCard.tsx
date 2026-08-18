/**
 * J.A.R.V.I.S. v3.0 — Activity Event Card (unified content surface)
 *
 * The operational timeline is NOT chat bubbles. Each event is a calm content
 * surface. Assistant ("jarvis") = dense dark surface; user ("command") = a
 * slightly different graphite surface; system/technical events are clearly
 * subordinate. Long answers stay readable; markdown renders cleanly; code
 * blocks are near-opaque with a hover copy button. Message actions (copy/
 * retry/details) appear on hover only.
 */

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Terminal, Sparkles, CheckCircle2, Circle, Loader2, RotateCw,
  AlertTriangle, Radio, Bot, Copy, RotateCcw, ChevronDown,
} from 'lucide-react';
import type { ActivityEvent, ActivityKind, TaskStep } from '@/types';
import { Markdown } from '@/components/Markdown/Markdown';
import { useUIState } from '@/hooks/useUIState';
import styles from './ActivityEventCard.module.css';

const META: Record<ActivityKind, { tag: string; icon: typeof Bot; cls: string }> = {
  command:   { tag: 'COMMAND',   icon: Terminal, cls: styles.kCommand },
  analysis:  { tag: 'ANALYSIS',  icon: Sparkles, cls: styles.kAnalysis },
  jarvis:    { tag: 'J.A.R.V.I.S.', icon: Bot, cls: styles.kJarvis },
  action:    { tag: 'ACTION',    icon: RotateCw, cls: styles.kAction },
  tool:      { tag: 'TOOL',      icon: RotateCw, cls: styles.kTool },
  result:    { tag: 'RESULT',    icon: CheckCircle2, cls: styles.kResult },
  system:    { tag: 'SYSTEM',    icon: Radio, cls: styles.kSystem },
  progress:  { tag: 'TASK',      icon: RotateCw, cls: styles.kProgress },
};

function StepRow({ step }: { step: TaskStep }) {
  const Icon = step.status === 'completed' ? CheckCircle2
    : step.status === 'failed' ? AlertTriangle
    : step.status === 'running' ? Loader2 : Circle;
  const cls = step.status === 'completed' ? styles.stepDone
    : step.status === 'failed' ? styles.stepFail
    : step.status === 'running' ? styles.stepRun : styles.stepPend;
  return (
    <div className={`${styles.step} ${cls}`}>
      <Icon size={13} className={step.status === 'running' ? styles.spin : ''} />
      <span>{step.label}</span>
    </div>
  );
}

interface Props {
  event: ActivityEvent;
  isStreaming: boolean;
  isLastJarvis?: boolean;
  onRetry?: () => void;
}

export function ActivityEventCard({ event, isStreaming, isLastJarvis, onRetry }: Props) {
  const [copied, setCopied] = useState(false);
  const { dispatch } = useUIState();
  const meta = META[event.kind];
  const Icon = meta.icon;
  const StatusIcon = event.status === 'running' ? Loader2
    : event.status === 'completed' ? CheckCircle2
    : event.status === 'failed' ? AlertTriangle : null;
  const hasDetails = !!event.detail || !!event.code;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(event.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch { /* clipboard unavailable */ }
  };

  return (
    <motion.article
      className={`${styles.node} ${meta.cls}`}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
      aria-label={meta.tag}
    >
      <header className={styles.head}>
        <span className={styles.icon}><Icon size={13} className={event.status === 'running' ? styles.spin : ''} /></span>
        <span className={styles.tag}>{event.label ?? meta.tag}</span>
        {StatusIcon && (
          <span className={styles.status}><StatusIcon size={13} className={event.status === 'running' ? styles.spin : ''} /></span>
        )}
        {event.detail && <span className={styles.detail}>{event.detail}</span>}

        {/* hover actions — copy / retry / details */}
        <span className={styles.actions}>
          {(event.kind === 'jarvis' || event.kind === 'analysis' || event.kind === 'result') && (
            <button className={styles.act} onClick={copy} aria-label="Копировать">
              {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
            </button>
          )}
          {isLastJarvis && onRetry && (
            <button className={styles.act} onClick={onRetry} aria-label="Повторить">
              <RotateCcw size={14} />
            </button>
          )}
          {hasDetails && (
            <button
              className={styles.act}
              onClick={() => dispatch({ type: 'SET_DRAWER_OPEN', payload: true })}
              aria-label="Показать детали в контексте"
              title="Детали"
            >
              <ChevronDown size={14} />
            </button>
          )}
        </span>
      </header>

      <div className={styles.body}>
        {event.kind === 'command' && (
          <div className={styles.command}>“{event.content}”</div>
        )}

        {event.kind === 'jarvis' && (
          <div className={styles.prose}>
            {event.content.trim() ? (
              <Markdown text={event.content} />
            ) : isStreaming ? (
              <span className={styles.typing} aria-label="J.A.R.V.I.S. печатает" role="status">
                <span /><span /><span />
              </span>
            ) : null}
            {isStreaming && event.content.trim() && <span className={styles.cursor} />}
          </div>
        )}

        {event.kind === 'analysis' && (
          <div className={styles.prose}><Markdown text={event.content} /></div>
        )}

        {(event.kind === 'action' || event.kind === 'tool') && (
          <div className={styles.technical}>
            <span className={styles.techText}>{event.content}</span>
            {event.code && <pre className={styles.code}>{event.code}</pre>}
          </div>
        )}

        {event.kind === 'result' && (
          <div className={styles.prose}><Markdown text={event.content} /></div>
        )}

        {event.kind === 'system' && (
          <div className={styles.system}>{event.content}</div>
        )}

        {event.kind === 'progress' && event.steps && (
          <div className={styles.steps}>
            {event.steps.map((s, i) => <StepRow key={i} step={s} />)}
          </div>
        )}

        {(event.tokens || event.durationMs || event.model) && (
          <div className={styles.foot}>
            {event.model && <span>{event.model.toUpperCase()}</span>}
            {event.tokens && <span>{event.tokens} tok</span>}
            {event.durationMs && <span>{(event.durationMs / 1000).toFixed(1)}s</span>}
          </div>
        )}
      </div>
    </motion.article>
  );
}
