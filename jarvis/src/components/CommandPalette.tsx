import { useEffect, useMemo, useRef, useState } from 'react';
import { Command, Maximize, PanelLeft, PanelRight, Settings, X } from 'lucide-react';
import styles from './CommandPalette.module.css';

type PaletteAction = {
  id: string;
  label: string;
  hint: string;
  icon: typeof Command;
  run: () => void;
};

interface Props {
  isFullscreen: boolean;
  onClose: () => void;
  onToggleFullscreen: () => void;
  onToggleSidebar: () => void;
  onToggleDrawer: () => void;
  onOpenSettings: () => void;
}

export function CommandPalette({
  isFullscreen,
  onClose,
  onToggleFullscreen,
  onToggleSidebar,
  onToggleDrawer,
  onOpenSettings,
}: Props) {
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const actions = useMemo<PaletteAction[]>(() => [
    {
      id: 'fullscreen',
      label: isFullscreen ? 'Выйти из полноэкранного режима' : 'Полноэкранный режим',
      hint: 'Окно',
      icon: Maximize,
      run: onToggleFullscreen,
    },
    { id: 'sidebar', label: 'Переключить боковую панель', hint: 'Вид', icon: PanelLeft, run: onToggleSidebar },
    { id: 'drawer', label: 'Переключить контекстную панель', hint: 'Вид', icon: PanelRight, run: onToggleDrawer },
    { id: 'settings', label: 'Открыть настройки', hint: 'Система', icon: Settings, run: onOpenSettings },
  ], [isFullscreen, onOpenSettings, onToggleDrawer, onToggleFullscreen, onToggleSidebar]);

  const filtered = actions.filter((action) =>
    `${action.label} ${action.hint}`.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase()),
  );

  const run = (action: PaletteAction) => {
    action.run();
    onClose();
  };

  return (
    <div className={styles.overlay} role="presentation" onMouseDown={onClose}>
      <section
        className={styles.panel}
        role="dialog"
        aria-modal="true"
        aria-label="Палитра команд"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className={styles.searchRow}>
          <Command size={18} aria-hidden="true" />
          <input
            ref={inputRef}
            className={styles.input}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Escape') onClose();
              if (event.key === 'Enter' && filtered[0]) run(filtered[0]);
            }}
            placeholder="Выполнить команду…"
            aria-label="Поиск команд"
          />
          <kbd>Esc</kbd>
          <button className={styles.close} onClick={onClose} aria-label="Закрыть палитру">
            <X size={16} />
          </button>
        </div>
        <div className={styles.results} role="listbox" aria-label="Доступные команды">
          {filtered.length === 0 && <div className={styles.empty}>Команды не найдены</div>}
          {filtered.map((action) => {
            const Icon = action.icon;
            return (
              <button key={action.id} className={styles.action} onClick={() => run(action)} role="option">
                <Icon size={17} aria-hidden="true" />
                <span className={styles.actionLabel}>{action.label}</span>
                <span className={styles.hint}>{action.hint}</span>
              </button>
            );
          })}
        </div>
        <div className={styles.footer}><span><kbd>Enter</kbd> выполнить</span><span><kbd>Ctrl/Cmd</kbd> + <kbd>K</kbd> открыть</span></div>
      </section>
    </div>
  );
}

export type { Props as CommandPaletteProps };
