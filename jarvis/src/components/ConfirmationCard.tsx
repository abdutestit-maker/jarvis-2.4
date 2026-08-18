/** J.A.R.V.I.S. v3.0 — Confirmation Card (HIGH-risk pending operation). */

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, Check, X } from 'lucide-react';
import type { PendingConfirmation } from '@/types';
import styles from './ConfirmationCard.module.css';

interface Props {
  confirmation: PendingConfirmation;
  timeoutMs?: number;
  onResolve: (approved: boolean) => void;
}

export function ConfirmationCard({ confirmation, timeoutMs = 30000, onResolve }: Props) {
  const [remaining, setRemaining] = useState(Math.round(timeoutMs / 1000));
  const riskLevel = confirmation.risk?.level ?? 'high';

  useEffect(() => {
    const start = Date.now();
    const id = window.setInterval(() => {
      const left = timeoutMs - (Date.now() - start);
      setRemaining(Math.max(0, Math.round(left / 1000)));
      if (left <= 0) {
        window.clearInterval(id);
        onResolve(false);
      }
    }, 1000);
    return () => window.clearInterval(id);
  }, [timeoutMs, onResolve]);

  const progress = Math.max(0, Math.min(1, remaining / (timeoutMs / 1000)));

  return (
    <div className={styles.overlay}>
      <motion.section
        role="alertdialog"
        aria-modal="true"
        aria-label="Требуется подтверждение действия"
        className={styles.card}
        initial={{ opacity: 0, y: 18, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.98 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className={styles.dangerEdge} aria-hidden="true" />

        <header className={styles.header}>
          <span className={styles.iconWrap}><AlertTriangle size={18} aria-hidden="true" /></span>
          <span className={styles.title}>ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ</span>
          <span className={styles.risk} data-level={riskLevel}>{riskLevel.toUpperCase()}</span>
        </header>

        <p className={styles.prompt}>{confirmation.prompt}</p>

        {confirmation.tool && (
          <p className={styles.tool}>Инструмент: <code>{confirmation.tool}</code></p>
        )}

        <div className={styles.timer} role="timer" aria-label={`Автоотклонение через ${remaining} секунд`}>
          <div className={styles.timerTop}>
            <span>Автоотклонение через</span>
            <strong>{remaining}с</strong>
          </div>
          <div className={styles.timerBar} aria-hidden="true">
            <motion.span
              className={styles.timerFill}
              initial={false}
              animate={{ width: `${progress * 100}%` }}
              transition={{ duration: 0.9, ease: 'linear' }}
            />
          </div>
        </div>

        <div className={styles.actions}>
          <button className={styles.approve} onClick={() => onResolve(true)}>
            <Check size={15} /> Выполнить
          </button>
          <button className={styles.reject} onClick={() => onResolve(false)}>
            <X size={15} /> Отклонить
          </button>
        </div>
      </motion.section>
    </div>
  );
}
