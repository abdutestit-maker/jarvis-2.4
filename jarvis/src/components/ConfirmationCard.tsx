/** J.A.R.V.I.S. v3.0 — Confirmation Card (HIGH-risk pending operation). */

import { useEffect, useState } from 'react';
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

  return (
    <div className={styles.overlay}>
      <section role="alertdialog" aria-modal="true" aria-label="Требуется подтверждение действия" className={styles.card}>
        <header className={styles.header}>
          <AlertTriangle size={18} className={styles.icon} aria-hidden="true" />
          <span className={styles.title}>ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ</span>
          <span className={styles.risk} data-level={riskLevel}>{riskLevel.toUpperCase()}</span>
        </header>

        <p className={styles.prompt}>{confirmation.prompt}</p>

        {confirmation.tool && (
          <p className={styles.tool}>Инструмент: <code>{confirmation.tool}</code></p>
        )}

        <div className={styles.timer} role="timer" aria-label={`Автоотклонение через ${remaining} секунд`}>
          <span>Автоотклонение через</span>
          <strong>{remaining}с</strong>
        </div>

        <div className={styles.actions}>
          <button className={styles.approve} onClick={() => onResolve(true)}>
            <Check size={15} /> Выполнить
          </button>
          <button className={styles.reject} onClick={() => onResolve(false)}>
            <X size={15} /> Отклонить
          </button>
        </div>
      </section>
    </div>
  );
}