/**
 * J.A.R.V.I.S. v3.0 — Settings Panel (frontend-only)
 * Theme · Panel transparency · Reduce motion · Personal background · Honorific.
 * No backend dependency. Reduce-motion is also respected via OS preference
 * (ThemeProvider merges system + user setting).
 */

import { useState, type ChangeEvent } from 'react';
import { motion } from 'framer-motion';
import { X, Sun, Moon, Layers, Crown, User } from 'lucide-react';
import { useUIState } from '@/hooks/useUIState';
import { useTheme } from '@/stores/themeStore';
import { useFocusTrap } from '@/hooks/useFocusTrap';
import type { ThemeName } from '@/types';
import styles from './SettingsPanel.module.css';

const THEMES: { id: ThemeName; label: string; icon: typeof Sun }[] = [
  { id: 'ivory', label: 'Ivory', icon: Sun },
  { id: 'midnight', label: 'Midnight', icon: Moon },
  { id: 'glass', label: 'Glass', icon: Layers },
  { id: 'olympus', label: 'Olympus', icon: Crown },
  { id: 'personal', label: 'Personal', icon: User },
];

function themeSwatch(t: ThemeName): string {
  switch (t) {
    case 'ivory': return 'linear-gradient(135deg,#f4f6fa,#e3e8f0)';
    case 'midnight': return 'linear-gradient(135deg,#0b0d18,#161a2a)';
    case 'glass': return 'linear-gradient(135deg,#0a0e1a,#1a2238)';
    case 'olympus': return 'linear-gradient(135deg,#0a0a1e,#1a1640)';
    case 'personal': return 'linear-gradient(135deg,#1a1030,#2a1a4a)';
  }
}

export function SettingsPanel() {
  const { dispatch } = useUIState();
  const { settings, setTheme, setTransparency, setReduceMotion, setBackgroundUrl, profile, updateProfile } = useTheme();
  const [honorific, setHonorific] = useState(profile?.honorific ?? 'сэр');

  const close = () => dispatch({ type: 'SET_SETTINGS_OPEN', payload: false });
  const panelRef = useFocusTrap<HTMLDivElement>(true, { onEscape: close, scrollLock: true, trap: true });

  const onBgPick = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const url = URL.createObjectURL(f);
    setBackgroundUrl(url);
  };

  return (
    <motion.div
      ref={panelRef}
      key="settings"
      className={styles.overlay}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={close}
        role="dialog"
        aria-modal="true"
        aria-label="Настройки"
      >
        <motion.div
          className={styles.panel}
          initial={{ y: 24, opacity: 0, scale: 0.98 }}
          animate={{ y: 0, opacity: 1, scale: 1 }}
          exit={{ y: 24, opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className={styles.header}>
            <h2 className={styles.title}>Настройки</h2>
            <button className={styles.close} onClick={close} aria-label="Закрыть">
              <X size={18} />
            </button>
          </div>

          <div className={styles.body}>
            <section className={styles.group}>
              <label className={styles.label}>Тема</label>
              <div className={styles.themes}>
                {THEMES.map((t) => (
                  <button
                    key={t.id}
                    className={`${styles.theme} ${settings.theme === t.id ? styles.themeActive : ''}`}
                    onClick={() => setTheme(t.id)}
                    aria-pressed={settings.theme === t.id}
                  >
                    <span className={styles.swatch} style={{ background: themeSwatch(t.id) }} />
                    <span className={styles.themeLabel}>{t.label}</span>
                  </button>
                ))}
              </div>
            </section>

            <section className={styles.group}>
              <label className={styles.label}>
                Прозрачность панелей
                <span className={styles.value}>{Math.round((1 - settings.transparency) * 100)}% плотность</span>
              </label>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={settings.transparency}
                onChange={(e) => setTransparency(Number(e.target.value))}
                className={styles.slider}
                aria-label="Прозрачность панелей"
              />
              <p className={styles.hint}>Содержимое сообщений остаётся плотным — текст не теряет читаемость.</p>
            </section>

            <section className={styles.group}>
              <label className={styles.toggle}>
                <input
                  type="checkbox"
                  checked={settings.reduceMotion}
                  onChange={(e) => setReduceMotion(e.target.checked)}
                />
                <span>Уменьшить анимацию (Reduce Motion)</span>
              </label>
              <p className={styles.hint}>Также наследуется из системной настройки «Уменьшить движение».</p>
            </section>

            {settings.theme === 'personal' && (
              <section className={styles.group}>
                <label className={styles.label}>Фон (Personal)</label>
                <label className={styles.fileBtn}>
                  Загрузить изображение
                  <input type="file" accept="image/*" hidden onChange={onBgPick} />
                </label>
                {settings.backgroundUrl && (
                  <button className={styles.resetBtn} onClick={() => setBackgroundUrl(undefined)}>
                    Сбросить фон
                  </button>
                )}
              </section>
            )}

            <section className={styles.group}>
              <label className={styles.label}>Обращение</label>
              <input
                className={styles.text}
                value={honorific}
                onChange={(e) => setHonorific(e.target.value)}
                onBlur={() => profile && updateProfile({ honorific: honorific.trim() || 'сэр' })}
                placeholder="сэр"
                aria-label="Обращение"
              />
              <p className={styles.hint}>Как J.A.R.V.I.S. обращается к вам (например: сэр).</p>
            </section>
          </div>
        </motion.div>
      </motion.div>
  );
}
